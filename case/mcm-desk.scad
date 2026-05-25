// Mid-century modern desktop case — ESP32-2424S012 round clock
// Board: ~38.5 x 37 mm PCB, ~32.4 mm visible display, USB-C on bottom edge
//
// Orientation: display faces UP (+Z), tripod legs DOWN (-Z), USB on underside
// Print: legs on build plate, display hole facing up
// Assembly: slide module in from the bottom; USB-C exits through underside slot

/* [Board] */
pcb_w           = 38.5;
pcb_d           = 37.0;
pcb_thickness   = 11.0;
display_dia     = 32.4;
clearance       = 0.55;

/* [Case proportions] */
wall            = 2.2;
bezel_reveal    = 1.0;
body_od         = 52;
body_height     = 40;
taper_ratio     = 1.1;
collar_h        = 5;

leg_h           = 24;
leg_od          = 7;
leg_splay       = 12;
leg_inset       = 15;

/* [USB underside] */
usb_slot_w      = 14.5;
usb_slot_h      = 9;
usb_channel_h   = 6;
usb_channel_w   = 14;

/* [BOOT — back-right on PCB when display faces up] */
boot_hole_d     = 4.2;
boot_x          = 12;
boot_y          = -10;

part = "preview"; // [preview, body, all]

$fn = 72;

pocket_w        = pcb_w + clearance;
pocket_d        = pcb_d + clearance;
pocket_h        = pcb_thickness + clearance + 2;
window_d        = display_dia + 0.6;
body_od_base    = body_od * taper_ratio;
base_rim_h      = 4;
z_top           = base_rim_h + body_height;

module pcb_pocket() {
  translate([0, 0, pocket_h / 2])
    cube([pocket_w, pocket_d, pocket_h + 0.01], center = true);
}

module display_aperture() {
  translate([0, 0, z_top - 2])
    cylinder(h = collar_h + 30, d = window_d, center = false);
}

module top_bezel_collar() {
  translate([0, 0, z_top])
    difference() {
      cylinder(h = collar_h, d = body_od, center = false);
      translate([0, 0, -0.01])
        cylinder(h = collar_h + 0.02, d = window_d + bezel_reveal * 2);
    }
}

// USB at bottom of PCB (+Y back edge when module inserted)
module usb_underside() {
  translate([0, pocket_d / 2 - 5, -0.01])
    cube([usb_slot_w, usb_slot_h + 4, usb_slot_h + base_rim_h + 1], center = false);
  translate([0, body_od_base / 2 + 2, usb_channel_h / 2])
    cube([usb_channel_w, usb_channel_h + 16, usb_channel_h], center = true);
  translate([0, 0, -0.01])
    cylinder(h = base_rim_h + 1.5, d = body_od_base - 6, center = false);
}

module boot_hole() {
  translate([boot_x, boot_y, z_top * 0.45])
    rotate([0, 55, 0])
      cylinder(h = 16, d = boot_hole_d, center = true, $fn = 32);
}

module waist_groove(z) {
  translate([0, 0, z])
    rotate_extrude($fn = 120)
      translate([body_od / 2 - 0.15, 0])
        circle(r = 0.5, $fn = 14);
}

module leg(a) {
  rotate([0, 0, a])
    translate([leg_inset, 0, 0])
      rotate([leg_splay, 0, 0])
        translate([0, 0, -leg_h])
          cylinder(h = leg_h + 1, d = leg_od, $fn = 36);
}

module tripod() {
  for (a = [0, 120, 240])
    leg(a);
  for (a = [0, 120, 240])
    rotate([0, 0, a])
      translate([leg_inset, 0, -leg_h - 0.8])
        rotate([leg_splay, 0, 0])
          sphere(d = leg_od + 1.4, $fn = 24);
}

module main_shell() {
  difference() {
    union() {
      translate([0, 0, base_rim_h])
        cylinder(h = body_height, d1 = body_od_base, d2 = body_od, center = false);
      cylinder(h = base_rim_h, d = body_od_base + 3, center = false);
      top_bezel_collar();
      tripod();
    }
    pcb_pocket();
    display_aperture();
    usb_underside();
    boot_hole();
    waist_groove(base_rim_h + body_height * 0.42);
    translate([0, 0, base_rim_h + 3])
      cylinder(h = body_height, d = body_od - 2 * wall - 6, center = false);
  }
}

module preview_stand() {
  %main_shell();
  color("BurlyWood", 0.4)
    translate([0, 0, pocket_h / 2])
      cube([pcb_w, pcb_d, pcb_thickness], center = true);
  color("SteelBlue", 0.35)
    translate([0, 0, pocket_h + 1.5])
      cylinder(h = 2, d = display_dia, center = true);
}

if (part == "preview") {
  preview_stand();
} else {
  main_shell();
}
