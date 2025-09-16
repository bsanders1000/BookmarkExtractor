#!/usr/bin/env python3
"""
Analyzer Registry - Manages available analyzers
"""
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class AnalyzerRegistry:
    """Registry for managing analyzers"""
    
    def __init__(self):
        self._analyzers: Dict[str, Any] = {}
        
    def register(self, analyzer_class) -> None:
        """Register an analyzer class"""
        try:
            # Create instance to get a human-friendly name, with safe fallbacks
            instance = analyzer_class()
            name = None
            # Prefer an explicit get_name() method if available
            if hasattr(instance, "get_name") and callable(getattr(instance, "get_name")):
                try:
                    name = instance.get_name()
                except Exception:
                    name = None
            # Fallback to a class attribute 'name'
            if not name:
                name = getattr(instance, "name", None)
            # Final fallback to class name
            if not name:
                name = analyzer_class.__name__

            self._analyzers[name] = analyzer_class
            logger.info(f"Registered analyzer: {name}")
        except Exception as e:
            logger.error(f"Failed to register analyzer {analyzer_class}: {e}")
            
    def get_analyzer_by_name(self, name: str):
        """Get an analyzer instance by name"""
        if name in self._analyzers:
            return self._analyzers[name]()
        return None
        
    def list_analyzer_names(self) -> List[str]:
        """List all registered analyzer names"""
        return list(self._analyzers.keys())
        
    def is_available(self, name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Check if an analyzer is available (has dependencies, API keys, etc.)"""
        try:
            analyzer_class = self._analyzers.get(name)
            if not analyzer_class:
                return False
                
            # Create instance and check if it can run
            instance = analyzer_class()
            
            # For Gemini analyzer, check API key availability
            if hasattr(instance, '_get_api_key'):
                # Get analyzer-specific config
                analyzer_config = (config or {}).get(name, {})
                api_key = instance._get_api_key(analyzer_config, None)
                return bool(api_key)
                
            return True
        except Exception as e:
            logger.error(f"Error checking availability for {name}: {e}")
            return False

# Global registry instance
_registry = AnalyzerRegistry()

def register(analyzer_class) -> None:
    """Register an analyzer"""
    _registry.register(analyzer_class)

def get_analyzer_by_name(name: str):
    """Get an analyzer by name"""
    return _registry.get_analyzer_by_name(name)

def list_analyzer_names(config: Optional[Dict[str, Any]] = None) -> List[str]:
    """List available analyzer names"""
    all_names = _registry.list_analyzer_names()
    if config is None:
        return all_names
    
    # Filter by availability
    available = []
    for name in all_names:
        if _registry.is_available(name, config):
            available.append(name)
    return available

# Auto-register available analyzers
def _auto_register():
    """Auto-register available analyzers"""
    # Gemini (LLM) analyzer
    try:
        from analyzers.gemini_topic_analyzer import GeminiTopicAnalyzer
        register(GeminiTopicAnalyzer)
    except ImportError as e:
        logger.debug(f"Gemini analyzer not available: {e}")

    # BERTopic single-document analyzer
    try:
        from analyzers.bertopic_single import BERTopicSingleDocAnalyzer
        register(BERTopicSingleDocAnalyzer)
    except ImportError as e:
        logger.debug(f"BERTopic analyzer not available: {e}")

    # LDA single-document analyzer
    try:
        from analyzers.lda_single import LDASingleDocAnalyzer
        register(LDASingleDocAnalyzer)
    except ImportError as e:
        logger.debug(f"LDA analyzer not available: {e}")

# Register analyzers on module import
_auto_register()