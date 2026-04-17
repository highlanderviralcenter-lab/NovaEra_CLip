#!/usr/bin/env python3
"""
ClipFusion Memory Manager
Otimizado para: 8GB RAM física + 4GB ZRAM (zstd)
Modos: simple (limiar clássico) ou advanced (regras completas)
"""

import os
import sys
import gc
import time
import threading
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger('ClipFusionMemory')

@dataclass
class MemoryStatus:
    ram_total_gb: float
    ram_used_gb: float
    ram_free_gb: float
    ram_percent: float
    zram_total_gb: float
    zram_used_gb: float
    zram_percent: float
    effective_available_gb: float
    system_pressure: str  # 'normal', 'warning', 'critical', 'emergency'

class MemoryManager8GB:
    """
    Gerenciador de memória para sistemas 8GB + ZRAM
    """
    
    _instance = None
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.mode = self.config.get('mode', 'simple')  # 'simple' ou 'advanced'
        
        if self.mode == 'simple':
            # Limiar perfeito (sem pausas agressivas)
            self.max_ram_gb = 6.0
            self.emergency_threshold = 7.5
            self.critical_threshold = 7.8
            self.zram_threshold_percent = 95
        else:
            # Modo avançado com todas as proteções
            self.max_ram_gb = self.config.get('max_ram_gb', 6.0)
            self.emergency_threshold = self.config.get('emergency_threshold_gb', 7.0)
            self.critical_threshold = self.config.get('critical_threshold_gb', 7.5)
            self.zram_threshold_percent = self.config.get('zram_threshold_percent', 80)
        
        self._lock = threading.Lock()
        self._emergency_mode = False
        self._allocated_mb = 0
        self._allocation_map = {}
        
        self.stats = {
            'gc_collections': 0,
            'emergency_activations': 0,
            'paused_operations': 0
        }
        
        self._detect_zram()
    
    @classmethod
    def get_instance(cls, config=None):
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance
    
    def _detect_zram(self):
        self.zram_device = None
        self.zram_compressed = 0
        try:
            for i in range(8):
                zram_path = f"/sys/block/zram{i}/"
                if os.path.exists(zram_path):
                    self.zram_device = f"zram{i}"
                    break
            if self.zram_device:
                logger.info(f"ZRAM detectado: {self.zram_device}")
            else:
                logger.warning("ZRAM não detectado")
        except Exception as e:
            logger.error(f"Erro detectando ZRAM: {e}")
    
    def _read_zram_stats(self) -> Tuple[float, float]:
        if not self.zram_device:
            return 0.0, 0.0
        try:
            with open(f"/sys/block/{self.zram_device}/disksize", 'r') as f:
                total_bytes = int(f.read().strip())
            mm_stat_path = f"/sys/block/{self.zram_device}/mm_stat"
            if os.path.exists(mm_stat_path):
                with open(mm_stat_path, 'r') as f:
                    stats = f.read().strip().split()
                    used_bytes = int(stats[2]) if len(stats) > 2 else 0
            else:
                with open(f"/sys/block/{self.zram_device}/mem_used_total", 'r') as f:
                    used_bytes = int(f.read().strip())
            return total_bytes / (1024**3), used_bytes / (1024**3)
        except Exception as e:
            logger.error(f"Erro lendo ZRAM: {e}")
            return 0.0, 0.0
    
    def get_status(self) -> MemoryStatus:
        import psutil
        mem = psutil.virtual_memory()
        ram_total = mem.total / (1024**3)
        ram_used = mem.used / (1024**3)
        ram_free = mem.available / (1024**3)
        
        zram_total, zram_used = self._read_zram_stats()
        
        zram_usage_ratio = (zram_used / zram_total) if zram_total > 0 else 0
        zram_efficiency = max(0.5, 0.9 - zram_usage_ratio * 0.5) if self.mode == 'advanced' else 0.8
        zram_effective = (zram_total - zram_used) * zram_efficiency if zram_total > 0 else 0
        effective_available = ram_free + max(0, zram_effective)
        
        if ram_used > self.critical_threshold or (zram_total > 0 and (zram_used/zram_total)*100 > 90):
            pressure = 'emergency'
        elif ram_used > self.emergency_threshold or (zram_total > 0 and (zram_used/zram_total)*100 > self.zram_threshold_percent):
            pressure = 'critical'
        elif ram_used > self.max_ram_gb:
            pressure = 'warning'
        elif self.mode == 'advanced' and ram_free < 1.0 and pressure == 'normal':
            pressure = 'warning'
        else:
            pressure = 'normal'
        
        return MemoryStatus(
            ram_total_gb=ram_total,
            ram_used_gb=ram_used,
            ram_free_gb=ram_free,
            ram_percent=mem.percent,
            zram_total_gb=zram_total,
            zram_used_gb=zram_used,
            zram_percent=(zram_used/zram_total)*100 if zram_total > 0 else 0,
            effective_available_gb=effective_available,
            system_pressure=pressure
        )
    
    def request_allocation(self, mb_required: int, priority: str = 'normal', component: str = 'unknown') -> bool:
        with self._lock:
            status = self.get_status()
            if status.system_pressure == 'emergency' and priority != 'critical':
                return False
            projected_used = status.ram_used_gb + (mb_required / 1024)
            if projected_used > self.critical_threshold:
                if priority != 'critical':
                    return False
            if projected_used > self.max_ram_gb and priority == 'low':
                return False
            self._allocated_mb += mb_required
            self._allocation_map[component] = self._allocation_map.get(component, 0) + mb_required
            return True
    
    def release_memory(self, mb_released: int, component: str = 'unknown'):
        with self._lock:
            self._allocated_mb = max(0, self._allocated_mb - mb_released)
            if component in self._allocation_map:
                self._allocation_map[component] = max(0, self._allocation_map[component] - mb_released)
            if mb_released > 500:
                self._soft_cleanup()
    
    def _soft_cleanup(self):
        gc.collect(0)
        self.stats['gc_collections'] += 1
    
    def _aggressive_cleanup(self):
        logger.info("Executando limpeza agressiva")
        gc.collect(2)
        self.stats['gc_collections'] += 1
    
    def enter_emergency_mode(self):
        if not self._emergency_mode:
            logger.critical("Modo emergência ativado")
            self._emergency_mode = True
            self.stats['emergency_activations'] += 1
    
    def exit_emergency_mode(self):
        if self._emergency_mode:
            logger.info("Saindo do modo emergência")
            self._emergency_mode = False
    
    def get_whisper_model(self, video_duration_minutes: float, user_choice: str = None) -> str:
        status = self.get_status()
        if user_choice and user_choice in ['tiny', 'base', 'small'] and status.system_pressure != 'emergency':
            return user_choice
        if status.system_pressure in ['critical', 'emergency'] or self._emergency_mode:
            return "tiny"
        if video_duration_minutes > 60:
            if status.effective_available_gb < 3.0:
                return "tiny"
            if status.effective_available_gb > 4.0:
                return "small"
            return "base"
        if video_duration_minutes > 30 and status.effective_available_gb > 4.0:
            return "base"
        return "tiny"
    
    def get_render_threads(self) -> int:
        status = self.get_status()
        if status.system_pressure == 'emergency':
            return 1
        if self.mode == 'advanced':
            if status.effective_available_gb > 5.0 and status.ram_free_gb > 2.0:
                return min(3, os.cpu_count() or 2)
            elif status.effective_available_gb > 2.0 and status.ram_free_gb > 1.0:
                return 2
            else:
                return 1
        else:
            return 2
    
    def check_render_chunk(self, chunk_size_mb: int = 500) -> bool:
        return self.request_allocation(chunk_size_mb, priority='normal', component='render')
    
    def render_complete(self, chunk_size_mb: int = 500):
        self.release_memory(chunk_size_mb, component='render')
    
    def should_pause(self) -> bool:
        status = self.get_status()
        if status.system_pressure in ['critical', 'emergency']:
            return True
        if self.mode == 'advanced':
            if status.ram_free_gb < 1.0 or status.zram_percent > 80:
                return True
        return False
    
    def wait_if_needed(self, timeout: int = 300):
        start = time.time()
        while self.should_pause():
            if time.time() - start > timeout:
                raise TimeoutError("Timeout aguardando memória")
            logger.info("Aguardando liberação de memória...")
            time.sleep(10)
            self._aggressive_cleanup()
    
    def get_gui_status(self) -> str:
        status = self.get_status()
        ram_used = status.ram_used_gb
        ram_max = self.max_ram_gb
        zram_used = status.zram_used_gb
        zram_total = status.zram_total_gb
        color = "green"
        if status.system_pressure == 'warning':
            color = "yellow"
        elif status.system_pressure in ['critical', 'emergency']:
            color = "red"
        return (f"RAM: {ram_used:.1f}/{ram_max:.1f}GB | "
                f"ZRAM: {zram_used:.1f}/{zram_total:.1f}GB | "
                f"Pressão: {status.system_pressure}")

# Singleton
_memory_manager = None

def get_memory_manager(config: Optional[Dict] = None) -> MemoryManager8GB:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager8GB.get_instance(config)
    return _memory_manager