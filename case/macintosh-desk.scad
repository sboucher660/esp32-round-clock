// Macintosh-style desktop case for ESP32-2424S012 round clock
// Board ref: ~37.0 x 38.5 mm PCB, ~32.4 mm visible round display
//
// Print: PLA/PETG, 0.2 mm layers, 3 walls, 15% infill (20% base)
// Export parts: OpenSCAD -> F7 on each part name at bottom
//
// Assembly: slide module in from BACK, push until display seats in front bezel.

/* [Board] */
pcb_w           = 38.5;
pcb_d           = 37.0;
pcb_thickness   = 11.0;
display_dia     = 32.4;
clearance       = 0.5;

/* [Case style] */
body_w          = 96;     // overall width
body_h          = 118;    // overall height (monitor + chin)
body_d          = 78;     // depth front to back
wall            = 2.4;
bezel_thick     = 5.0;
chin_h          = 22;     // "Macintosh" chin below screen
screen_inset    = 8;      // recess depth for display module

/* [Front window] */
window_d        = display_dia + 1.2;   // visible round hole
pocket_w        = pcb_w + clearance;
pocket_d        = pcb_d + clearance;
pocket_depth    = pcb_thickness + clearance + 2;

/* [USB / button] */
usb_slot_w      = 14;
usb_slot_h      = 6;
boot_hole_d     = 4;      // GPIO 9 boot button access (back)

/* [Which part to render] */
part = "preview"; // [preview, body, back, bezel_ring, all]

$fn = 80;

module rounded_mac_profile(w, h, r, t) {
  // Classic compact Mac front silhouette (rounded top, square chin)
  linear_extrude(t, center = false)
    hull() {
      translate([-w / 2 + r, -h / 2 + r]) circle(r = r);
      translate([w / 2 - r, -h / 2 + r]) circle(r = r);
      translate([-w / 2 + r, h / 2 - r]) circle(r = r);
      translate([w / 2 - r, h / 2 - r]) circle(r = r);
    }
}

module screen_pocket() {
  // Cavity that accepts the square PCB behind the round glass
  translate([0, chin_h / 2, -pocket_depth / 2])
    cube([pocket_w, pocket_d, pocket_depth + 0.01], center = true);
}

module display_window_cut() {
  translate([0, chin_h / 2, bezel_thick + 0.5])
    cylinder(h = body_d, d = window_d, center = false, $fn = 120);
}

module usb_cut() {
  // Bottom edge USB-C access (adjust position to match your board)
  translate([0, -body_h / 2 + 6, body_d - 18])
    cube([usb_slot_w, usb_slot_h, 20], center = true);
}

module boot_cut() {
  translate([pcb_w / 2 - 4, chin_h / 2 - 6, body_d - 1])
    cylinder(h = 20, d = boot_hole_d, center = true, $fn = 32);
}

module mac_body_shell() {
  difference() {
    union() {
      rounded_mac_profile(body_w, body_h, 14, body_d);
      // Solid chin / base lip
      translate([0, -body_h / 2 + chin_h / 2, 0])
        cube([body_w, chin_h, body_d], center = true);
    }
    // Hollow interior
    translate([0, 0, wall])
      rounded_mac_profile(body_w - wall * 2, body_h - wall * 2, 12, body_d - wall + 0.01);
    screen_pocket();
    display_window_cut();
    usb_cut();
    boot_cut();
    // Back opening is separate cover — leave rear access channel
    translate([0, 0, body_d - wall - 1])
      cube([body_w - 10, body_h - 10, wall + 2], center = true);
  }

  // Front bezel lip — display rests against this ring
  translate([0, chin_h / 2, 0])
    difference() {
      cylinder(h = bezel_thick, d = window_d + 6, $fn = 120);
      translate([0, 0, -0.01])
        cylinder(h = bezel_thick + 0.02, d = window_d, $fn = 120);
    }

  // Side rails to guide PCB when sliding in from back
  for (sx = [-1, 1])
    translate([sx * (pocket_w / 2 + 0.4), chin_h / 2, body_d / 2])
      cube([1.2, pocket_d - 4, body_d - bezel_thick - 6], center = true);
}

module mac_back_cover() {
  // Snap-on rear plate — glue small dots or use M3 tape
  difference() {
    translate([0, 0, 0])
      rounded_mac_profile(body_w - 1, body_h - 1, 12, 3.2);
    translate([0, chin_h / 2, -0.01])
      cube([pocket_w + 2, pocket_d + 2, 20], center = true);
    usb_cut();
  }
}

module mac_bezel_ring() {
  // Optional cosmetic ring (glue flush on front)
  difference() {
    cylinder(h = 2, d = window_d + 8, $fn = 120);
    translate([0, 0, -0.01])
      cylinder(h = 2.02, d = window_d, $fn = 120);
  }
}

module preview() {
  color("BurlyWood") mac_body_shell();
  %translate([0, chin_h / 2, body_d / 2]) cube([pocket_w, pocket_d, pcb_thickness], center = true);
  %translate([0, chin_h / 2, 2]) cylinder(h = 1, d = display_dia, $fn = 120);
  translate([0, 0, body_d + 4]) color("Tan") mac_back_cover();
}

if (part == "body") {
  mac_body_shell();
} else if (part == "back") {
  mac_back_cover();
} else if (part == "bezel_ring") {
  mac_bezel_ring();
} else if (part == "all") {
  translate([-55, 0, 0]) mac_body_shell();
  translate([55, 0, 0]) mac_back_cover();
  translate([0, 55, 0]) mac_bezel_ring();
} else {
  preview();
}
