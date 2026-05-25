// Mini Macintosh case — ESP32-2424S012 (1.28" round display, 38.5×37 mm PCB)
// Inspired by Thingiverse 6791318 (no keyboard, no mouse; that model uses a tiny OLED —
// this is sized for YOUR round GC9A01 module).
//
// HOW IT SITS ON YOUR DESK (read this first):
//
//        ┌─────────────────┐
//        │   ROUND SCREEN  │  ← you look at this (front, Z = 0)
//        │                 │
//        │    (chin)       │
//        └────────┬────────┘
//                 │ USB cable down through bottom slot
//              desk
//
//   X = left/right width    Y = height (chin at bottom)    Z = depth (back = far side)
//
//   Insert board: slide in from the BACK (high Z), display stops at front bezel.
//   USB-C: plug from UNDERNEATH (slot in bottom of chin).

/* [Board — measure with calipers if tight] */
pcb_w           = 38.5;
pcb_d           = 37.0;
pcb_thickness   = 11.0;
display_dia     = 32.4;
clearance       = 0.55;

/* [Shell — compact Mac proportions] */
body_w          = 92;
body_h          = 112;
body_d          = 74;
wall            = 2.4;
chin_h          = 24;
corner_r        = 13;
bezel_thick     = 5;

/* [USB on underside] */
usb_slot_w      = 15;
usb_slot_h      = 8;
usb_recess_z    = 14;

/* [BOOT — back-right when viewing screen] */
boot_hole_d     = 4.2;

part = "preview"; // [preview, body, back, all]

$fn = 80;

pocket_w        = pcb_w + clearance;
pocket_d        = pcb_d + clearance;
pocket_depth    = pcb_thickness + clearance + 2;
window_d        = display_dia + 1.0;
screen_y        = chin_h / 2 + 32;

// Side view profile (X wide × Y tall), extruded along Z = depth
module mac_profile_2d(w, h, r) {
  hull() {
    translate([-w / 2 + r, -h / 2 + r]) circle(r = r);
    translate([w / 2 - r, -h / 2 + r]) circle(r = r);
    translate([-w / 2 + r, h / 2 - r]) circle(r = r);
    translate([w / 2 - r, h / 2 - r]) circle(r = r);
  }
}

module mac_solid(w, h, r, depth) {
  linear_extrude(depth, center = false)
    mac_profile_2d(w, h, r);
}

// Cavity behind the round glass (board lives here)
module pcb_pocket() {
  translate([0, screen_y, body_d / 2])
    cube([pocket_w, pocket_d, pocket_depth], center = true);
}

// Round screen hole — tunnel from front (Z=0) through bezel depth
module screen_hole() {
  translate([0, screen_y, -0.01])
    cylinder(h = bezel_thick + 2, d = window_d, $fn = 120);
}

module front_bezel() {
  translate([0, screen_y, 0])
    difference() {
      cylinder(h = bezel_thick, d = window_d + 7, $fn = 120);
      translate([0, 0, -0.01])
        cylinder(h = bezel_thick + 0.02, d = window_d, $fn = 120);
    }
}

// USB-C access: opening in bottom of chin + path toward back
module usb_underside() {
  translate([0, -body_h / 2 + 7, usb_recess_z / 2])
    cube([usb_slot_w, usb_slot_h, usb_recess_z], center = true);
  translate([0, -body_h / 2 + 6, body_d - 10])
    cube([usb_slot_w, 6, 18], center = true);
}

module boot_hole() {
  translate([pcb_w / 2 - 3, screen_y - 8, body_d - 2])
    cylinder(h = 14, d = boot_hole_d, center = true, $fn = 32);
}

module chin_slot() {
  translate([0, -body_h / 2 + chin_h - 3, body_d / 2])
    cube([26, 2.2, body_d - 8], center = true);
}

module mac_body() {
  difference() {
    union() {
      mac_solid(body_w, body_h, corner_r, body_d);
      translate([0, -body_h / 2 + chin_h / 2, 0])
        cube([body_w, chin_h, body_d], center = true);
      front_bezel();
    }
    translate([0, 0, wall])
      mac_solid(body_w - wall * 2, body_h - wall * 2, corner_r - 2, body_d - wall);
    pcb_pocket();
    screen_hole();
    usb_underside();
    boot_hole();
    chin_slot();
    translate([0, 0, body_d - wall - 0.5])
      cube([body_w - 8, body_h - 8, wall + 1], center = true);
  }
  for (sx = [-1, 1])
    translate([sx * (pocket_w / 2 + 0.5), screen_y, body_d / 2])
      cube([1.5, pocket_d - 6, body_d - bezel_thick - 8], center = true);
}

module mac_back() {
  difference() {
    mac_solid(body_w - 1, body_h - 1, corner_r - 1, 3.2);
    translate([0, screen_y, -0.01])
      cube([pocket_w + 3, pocket_d + 3, 12], center = true);
    usb_underside();
  }
}

module preview() {
  color("Wheat") mac_body();
  color("Tan", 0.9) translate([0, 0, body_d + 3]) mac_back();
  color("SandyBrown", 0.45)
    translate([0, screen_y, body_d / 2])
      cube([pcb_w, pcb_d, pcb_thickness], center = true);
  color("LightSteelBlue", 0.5)
    translate([0, screen_y, bezel_thick / 2])
      cylinder(h = 1.5, d = display_dia, $fn = 120);
  // Arrow hints
  color("Red", 0.7)
    translate([0, screen_y, -6]) cylinder(h = 4, d = 2, $fn = 16);
  color("Blue", 0.7)
    translate([0, screen_y, body_d + 8]) cylinder(h = 4, d = 2, $fn = 16);
}

if (part == "body") {
  mac_body();
} else if (part == "back") {
  mac_back();
} else if (part == "all") {
  mac_body();
  translate([105, 0, 0]) mac_back();
} else {
  preview();
}
