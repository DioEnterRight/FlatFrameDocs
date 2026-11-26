// Location kits. Elevation sets (skill 5.1): a straight-on wall band over a floor band, built from at least four
// layers (back wall, furniture, the cast line, a foreground prop cropping a frame edge or a window with a view).
// Exteriors use sky / far scenery / mid scenery / ground / foreground. Each kit names specific props, wall items
// and a light recipe, so no location is a character in empty space.
export type Kit = {
  outdoor: boolean;
  wall?: string;
  wallPattern?: string;
  floor: string;
  floorPattern: string;
  window?: "city" | "street" | "field" | "night" | "sky" | "sea" | null;
  decor: string[]; // small wall items (3-6)
  furniture: string[]; // against the back wall
  light: "window_bands" | "lamp" | "ceiling" | "doorway" | "sun" | "moon";
  fg: string; // a foreground prop cropping an edge
  far?: "skyline" | "hills" | "flat" | "sea" | "dunes" | "stars" | "forest";
  mid?: string[];
};

export const KITS: Record<string, Kit> = {
  office: { outdoor: false, wall: "#C9C3A8", wallPattern: "panels", floor: "#6E4726", floorPattern: "planks", window: "city", decor: ["clock_wall", "calendar_wall", "picture_frame", "plaque"], furniture: ["filing_cabinet", "desk", "plant"], light: "window_bands", fg: "plant" },
  home: { outdoor: false, wall: "#D9C2A0", wallPattern: "wallpaper", floor: "#7A5232", floorPattern: "planks", window: "street", decor: ["picture_frame", "clock_wall", "pinned_paper"], furniture: ["bookshelf", "radio_old", "lamp_floor"], light: "lamp", fg: "lamp_floor" },
  lab: { outdoor: false, wall: "#CFD8D2", wallPattern: "tiles", floor: "#9AA5A0", floorPattern: "checker", window: "sky", decor: ["clock_wall", "pinned_paper", "plaque", "calendar_wall"], furniture: ["bookshelf", "desk", "plant"], light: "ceiling", fg: "flask" },
  archive: { outdoor: false, wall: "#7A6A55", wallPattern: "panels", floor: "#5B3A22", floorPattern: "planks", window: "night", decor: ["plaque", "clock_wall", "picture_frame"], furniture: ["bookshelf", "filing_cabinet", "bookshelf"], light: "lamp", fg: "lamp_desk" },
  bank: { outdoor: false, wall: "#B9B39A", wallPattern: "stone", floor: "#8C8577", floorPattern: "checker", window: null, decor: ["clock_wall", "plaque", "calendar_wall"], furniture: ["vault_door", "safe", "desk"], light: "ceiling", fg: "money_stack" },
  courtroom: { outdoor: false, wall: "#8C6A4F", wallPattern: "panels", floor: "#6E4726", floorPattern: "carpet", window: "sky", decor: ["clock_wall", "plaque", "picture_frame"], furniture: ["podium", "flag", "desk"], light: "window_bands", fg: "scales" },
  newsroom: { outdoor: false, wall: "#B7C2C4", wallPattern: "brick", floor: "#7D7A70", floorPattern: "tiles", window: "city", decor: ["clock_wall", "calendar_wall", "pinned_paper", "pinned_paper"], furniture: ["desk", "filing_cabinet", "tv_old"], light: "ceiling", fg: "typewriter" },
  workshop: { outdoor: false, wall: "#8E8A7E", wallPattern: "brick", floor: "#6F6B62", floorPattern: "concrete", window: "sky", decor: ["pinned_paper", "clock_wall", "calendar_wall"], furniture: ["crate", "barrel", "gear"], light: "window_bands", fg: "crate" },
  hall: { outdoor: false, wall: "#B5A37E", wallPattern: "stone", floor: "#7B0B1A", floorPattern: "carpet", window: "sky", decor: ["plaque", "picture_frame", "clock_wall"], furniture: ["flag", "podium", "flag"], light: "ceiling", fg: "microphone" },
  street: { outdoor: true, floor: "#5E5E5A", floorPattern: "road", decor: [], furniture: [], light: "sun", fg: "lamppost", far: "skyline", mid: ["house", "lamppost", "mailbox", "house"] },
  city_night: { outdoor: true, floor: "#3B3E46", floorPattern: "road", decor: [], furniture: [], light: "moon", fg: "lamppost", far: "skyline", mid: ["lamppost", "car_old", "mailbox"] },
  farm: { outdoor: true, floor: "#8C6A3F", floorPattern: "furrows", decor: [], furniture: [], light: "sun", fg: "wheat", far: "hills", mid: ["haystack", "fence", "tree", "wheat"] },
  outback: { outdoor: true, floor: "#C98E57", floorPattern: "sand", decor: [], furniture: [], light: "sun", fg: "bush", far: "flat", mid: ["wire_fence", "bush", "rock", "tree"] },
  camp: { outdoor: true, floor: "#7C8F4E", floorPattern: "grass", decor: [], furniture: [], light: "sun", fg: "crate", far: "hills", mid: ["tent", "flag", "crate", "truck"] },
  harbor: { outdoor: true, floor: "#8C6A4F", floorPattern: "planks", decor: [], furniture: [], light: "sun", fg: "barrel", far: "sea", mid: ["lighthouse", "crate", "barrel"] },
  desert: { outdoor: true, floor: "#D9B77E", floorPattern: "sand", decor: [], furniture: [], light: "sun", fg: "rock", far: "dunes", mid: ["pyramid", "rock"] },
  field: { outdoor: true, floor: "#7C8F4E", floorPattern: "grass", decor: [], furniture: [], light: "sun", fg: "bush", far: "forest", mid: ["tree", "fence", "bush"] },
  space: { outdoor: true, floor: "#8C8577", floorPattern: "concrete", decor: [], furniture: [], light: "moon", fg: "rock", far: "stars", mid: ["rocket", "satellite"] },
};

export const SET_KINDS = Object.keys(KITS);
