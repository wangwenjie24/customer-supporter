from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Optional

from langchain_core.runnables import RunnableConfig


@dataclass(kw_only=True)
class Configuration:

    user_title: str = ""
    user_id: str = ""
    
    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> Configuration:
        """Create a Configuration instance from a RunnableConfig object."""
        configurable = (config.get("configurable") or {}) if config else {}
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in configurable.items() if k in _fields})
