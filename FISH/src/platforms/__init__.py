"""Platforms 模組"""
from .base import BasePlatform
from .agoda import AgodaPlatform
from .booking import BookingPlatform

__all__ = ["BasePlatform", "AgodaPlatform", "BookingPlatform"]
