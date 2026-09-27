# -- coding: utf-8 --
"""CustomTkinter visual tokens."""

import customtkinter as ctk

COLORS = {
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "bg": "#F1F5F9",
    "surface": "#FFFFFF",
    "text": "#0F172A",
    "muted": "#64748B",
    "border": "#E2E8F0",
    "success": "#16A34A",
    "danger": "#DC2626",
}

SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}
FONT = ("Microsoft YaHei UI", 12)


def apply_appearance() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
