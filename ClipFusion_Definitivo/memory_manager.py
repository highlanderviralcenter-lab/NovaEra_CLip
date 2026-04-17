#!/usr/bin/env python3
"""
Memory manager otimizado para 8GB RAM física + ZRAM.

Regras centrais:
- soft limit: 5GB
- hard limit: 6GB
- economy mode: >7GB
- emergency stop: >7.5GB
"""

import gc
import os
import psutil
import threading


class MemoryManager8GB:
    def __init__(self, physical_ram=8, zram_gb=4):
        self.physical_ram = float(physical_ram)
        self.expected_zram_gb = float(zram_gb)
        self.soft_limit_gb = 5.0
        self.hard_limit_gb = 6.0
        self.economy_trigger_gb = 7.0
        self.emergency_trigger_gb = 7.5
        self.zram_pressure_threshold = 80.0
        self._lock = threading.Lock()
        self._economy_mode = False
        self._paused = False
        self._allocated_mb = 0
        self.runtime = {
            "max_render_threads": 2,
            "whisper_model": "tiny",
            "preview_enabled": True,
        }
        self._zram_device = self._detect_zram_device()

    def _detect_zram_device(self):
        base = "/sys/block"
        if not os.path.isdir(base):
            return None
        for name in os.listdir(base):
            if name.startswith("zram"):
                return name
        return None

    def _read_float(self, path, div=1.0):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return float(f.read().strip()) / div
        except Exception:
            return 0.0

    def _zram_stats(self):
        if not self._zram_device:
            return (0.0, 0.0, False)
        root = f"/sys/block/{self._zram_device}"
        total_gb = self._read_float(f"{root}/disksize", div=(1024 ** 3))
        used_gb = 0.0

        mm_stat = f"{root}/mm_stat"
        if os.path.exists(mm_stat):
            try:
                with open(mm_stat, "r", encoding="utf-8") as f:
                    parts = f.read().split()
                if len(parts) >= 3:
                    used_gb = float(parts[2]) / (1024 ** 3)
            except Exception:
                used_gb = 0.0
        else:
            used_gb = self._read_float(f"{root}/mem_used_total", div=(1024 ** 3))

        return (total_gb, used_gb, total_gb > 0.0)

    def get_available_ram(self):
        status = self.get_status()
        return status["effective_available_gb"]

    def _refresh_runtime_mode(self, status):
        ram_used = status["ram_used_gb"]
        zram_pct = status["zram_percent"]
        if ram_used >= self.emergency_trigger_gb or zram_pct >= 95.0:
            self._paused = True
            self.enter_emergency_mode()
            return
        if ram_used >= self.economy_trigger_gb or zram_pct >= self.zram_pressure_threshold:
            self.enter_emergency_mode()
            self._paused = False
            return

        self._economy_mode = False
        self._paused = False
        avail = status["ram_available_gb"]
        if avail < 3.0:
            threads = 1
        elif avail > 5.0:
            threads = 3
        else:
            threads = 2
        self.runtime.update({
            "max_render_threads": threads,
            "whisper_model": "tiny",
            "preview_enabled": True,
        })

    def request_allocation(self, mb_needed, priority="normal"):
        mb_needed = float(mb_needed)
        gb_needed = mb_needed / 1024.0
        with self._lock:
            status = self.get_status()
            self._refresh_runtime_mode(status)

            if self._paused and priority != "critical":
                gc.collect()
                return False

            projected = status["ram_used_gb"] + gb_needed
            if projected > self.hard_limit_gb and priority != "critical":
                gc.collect()
                return False
            if projected > self.soft_limit_gb and priority == "low":
                return False

            self._allocated_mb += mb_needed
            return True

    def release_allocation(self, mb_freed):
        with self._lock:
            self._allocated_mb = max(0, self._allocated_mb - float(mb_freed))

    def enter_emergency_mode(self):
        self._economy_mode = True
        self.runtime.update({
            "max_render_threads": 1,
            "whisper_model": "tiny",
            "preview_enabled": False,
        })
        gc.collect()

    def recommend_whisper_model(self, video_minutes, ask_small=False):
        status = self.get_status()
        available = status["effective_available_gb"]
        if self._economy_mode:
            return "tiny"
        if video_minutes > 60 and available > 6.0 and ask_small:
            return "small"
        if video_minutes > 20 and available > 4.0:
            return "base"
        return "tiny"

    def get_status(self):
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        ram_total_gb = mem.total / (1024 ** 3)
        ram_used_gb = mem.used / (1024 ** 3)
        ram_available_gb = mem.available / (1024 ** 3)
        zram_total_gb, zram_used_gb, zram_active = self._zram_stats()
        zram_percent = (zram_used_gb / zram_total_gb * 100.0) if zram_total_gb > 0 else 0.0
        zram_free_gb = max(0.0, zram_total_gb - zram_used_gb)

        # ZRAM-aware: capacidade efetiva considera RAM disponível + margem do zram livre.
        zram_weight = 1.0 if mem.percent >= 80.0 else 0.7
        effective_available = ram_available_gb + (zram_free_gb * zram_weight)
        pressure = "normal"
        if ram_used_gb >= self.emergency_trigger_gb or zram_percent >= 95.0:
            pressure = "emergency_stop"
        elif ram_used_gb >= self.economy_trigger_gb or zram_percent >= self.zram_pressure_threshold:
            pressure = "economy"
        elif ram_used_gb >= self.hard_limit_gb:
            pressure = "hard_limit"
        elif ram_used_gb >= self.soft_limit_gb:
            pressure = "soft_limit"

        return {
            "ram_total_gb": ram_total_gb,
            "ram_used_gb": ram_used_gb,
            "ram_available_gb": ram_available_gb,
            "ram_percent": mem.percent,
            "zram_active": zram_active,
            "zram_total_gb": zram_total_gb,
            "zram_used_gb": zram_used_gb,
            "zram_percent": zram_percent,
            "swap_used_gb": swap.used / (1024 ** 3),
            "swap_percent": swap.percent,
            "effective_available_gb": effective_available,
            "allocated_mb": self._allocated_mb,
            "mode": "economy" if self._economy_mode else "normal",
            "paused": self._paused,
            "pressure": pressure,
            "runtime": dict(self.runtime),
        }


_manager = None


def get_memory_manager():
    global _manager
    if _manager is None:
        _manager = MemoryManager8GB()
    return _manager
