// DFM Modern IDM Visual Theme in Pure Rust
// Authors: Rezanur <rezanurbinshamim@gmail.com>

use eframe::egui::{self, Color32, Margin, Rounding, Stroke, Visuals};

pub fn apply_theme(ctx: &egui::Context, dark_mode: bool) {
    let mut visuals = if dark_mode {
        Visuals::dark()
    } else {
        Visuals::light()
    };

    if dark_mode {
        // Modern IDM Dark Palette
        visuals.panel_fill = Color32::from_rgb(15, 19, 31);
        visuals.window_fill = Color32::from_rgb(18, 24, 38);
        visuals.window_stroke = Stroke::new(1.0_f32, Color32::from_rgb(35, 48, 75));
        visuals.override_text_color = Some(Color32::from_rgb(241, 245, 249));

        // Widget styling
        visuals.widgets.noninteractive.bg_fill = Color32::from_rgb(20, 26, 42);
        visuals.widgets.noninteractive.bg_stroke = Stroke::new(1.0_f32, Color32::from_rgb(35, 48, 75));
        visuals.widgets.noninteractive.rounding = Rounding::same(6.0);

        visuals.widgets.inactive.bg_fill = Color32::from_rgb(24, 32, 52);
        visuals.widgets.inactive.bg_stroke = Stroke::new(1.0_f32, Color32::from_rgb(45, 60, 95));
        visuals.widgets.inactive.rounding = Rounding::same(6.0);

        visuals.widgets.hovered.bg_fill = Color32::from_rgb(37, 99, 235);
        visuals.widgets.hovered.bg_stroke = Stroke::new(1.0_f32, Color32::from_rgb(96, 165, 250));
        visuals.widgets.hovered.rounding = Rounding::same(6.0);

        visuals.widgets.active.bg_fill = Color32::from_rgb(29, 78, 216);
        visuals.widgets.active.bg_stroke = Stroke::new(1.0_f32, Color32::from_rgb(59, 130, 246));
        visuals.widgets.active.rounding = Rounding::same(6.0);

        visuals.selection.bg_fill = Color32::from_rgb(37, 99, 235);
        visuals.selection.stroke = Stroke::new(1.0_f32, Color32::from_rgb(147, 197, 253));
    } else {
        // Modern IDM Light Palette
        visuals.panel_fill = Color32::from_rgb(248, 250, 252);
        visuals.window_fill = Color32::from_rgb(255, 255, 255);
        visuals.window_stroke = Stroke::new(1.0_f32, Color32::from_rgb(226, 232, 240));
        visuals.override_text_color = Some(Color32::from_rgb(15, 23, 42));

        visuals.widgets.noninteractive.bg_fill = Color32::from_rgb(241, 245, 249);
        visuals.widgets.noninteractive.bg_stroke = Stroke::new(1.0_f32, Color32::from_rgb(226, 232, 240));
        visuals.widgets.noninteractive.rounding = Rounding::same(6.0);

        visuals.widgets.inactive.bg_fill = Color32::from_rgb(255, 255, 255);
        visuals.widgets.inactive.bg_stroke = Stroke::new(1.0_f32, Color32::from_rgb(203, 213, 225));
        visuals.widgets.inactive.rounding = Rounding::same(6.0);

        visuals.widgets.hovered.bg_fill = Color32::from_rgb(239, 246, 255);
        visuals.widgets.hovered.bg_stroke = Stroke::new(1.0_f32, Color32::from_rgb(59, 130, 246));
        visuals.widgets.hovered.rounding = Rounding::same(6.0);

        visuals.widgets.active.bg_fill = Color32::from_rgb(37, 99, 235);
        visuals.widgets.active.bg_stroke = Stroke::new(1.0_f32, Color32::from_rgb(29, 78, 216));
        visuals.widgets.active.rounding = Rounding::same(6.0);

        visuals.selection.bg_fill = Color32::from_rgb(219, 234, 254);
        visuals.selection.stroke = Stroke::new(1.0_f32, Color32::from_rgb(59, 130, 246));
    }

    ctx.set_visuals(visuals);

    // Style adjustments
    let mut style = (*ctx.style()).clone();
    style.spacing.item_spacing = egui::vec2(8.0, 6.0);
    style.spacing.button_padding = egui::vec2(10.0, 6.0);
    style.spacing.window_margin = Margin::same(12.0);
    ctx.set_style(style);
}
