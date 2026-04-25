import { RoleType, Tone } from "./types";

export const toneClassMap: Record<Tone, string> = {
  navy: "tone-navy",
  teal: "tone-teal",
  coral: "tone-coral",
  green: "tone-green",
  violet: "tone-violet",
  gold: "tone-gold",
  pink: "tone-pink",
  muted: "tone-muted",
};

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatScore(value: number): string {
  return value.toFixed(2);
}

const taxonomyLabelMap: Record<string, string> = {
  "Bạn đọc": "Readers",
  "Bảo vệ người tiêu dùng": "Consumer Protection",
  "Bất động sản": "Real Estate",
  "Chính trị": "Politics",
  "Công nghệ": "Technology",
  "Dân tộc - Tôn giáo": "Ethnic & Religion",
  "Đời sống": "Lifestyle",
  "Du lịch": "Travel",
  "Giáo dục": "Education",
  "Kinh doanh": "Business",
  "Ô tô - Xe máy": "Cars & Bikes",
  "Pháp luật": "Law",
  "Sức khỏe": "Health",
  "Thế giới": "World",
  "Thể thao": "Sports",
  "Thị trường tiêu dùng": "Consumer Market",
  "Thời sự": "News",
  "Tuần Việt Nam": "Tuan Viet Nam",
  "Văn hóa - Giải trí": "Culture & Entertainment",
};

export function translateLabel(label: string): string {
  return taxonomyLabelMap[label] ?? label;
}

export function toneForLabel(label: string): Tone {
  const normalized = label.toLowerCase();
  if (normalized.includes("chính trị") || normalized.includes("thời sự")) {
    return "navy";
  }
  if (normalized.includes("công nghệ") || normalized.includes("ai")) {
    return "teal";
  }
  if (normalized.includes("giáo dục")) {
    return "gold";
  }
  if (normalized.includes("kinh doanh") || normalized.includes("thị trường")) {
    return "coral";
  }
  if (normalized.includes("văn hóa") || normalized.includes("giải trí")) {
    return "violet";
  }
  return "muted";
}

const sidebarHrefMap: Record<string, string> = {
  dashboard: "/editor/dashboard",
  review: "/editor/dashboard",
  classifier: "/editor/dashboard",
  admin: "/editor/admin",
  monitoring: "/scientist/monitoring",
  versions: "/scientist/versions",
  dataset: "/scientist/dataset",
};

const roleSidebarItems: Record<RoleType, Set<string>> = {
  "editor-admin": new Set(["dashboard", "review", "classifier", "admin"]),
  "data-scientist": new Set(["monitoring", "versions", "dataset"]),
};

const rolePathPrefixes: Record<RoleType, string[]> = {
  "editor-admin": ["/editor/dashboard", "/editor/review", "/editor/admin"],
  "data-scientist": ["/scientist/monitoring", "/scientist/versions", "/scientist/dataset"],
};

export function defaultPathForRole(role: RoleType): string {
  return role === "editor-admin" ? "/editor/dashboard" : "/scientist/monitoring";
}

export function isPathAllowedForRole(pathname: string, role: RoleType): boolean {
  return rolePathPrefixes[role].some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export function isSidebarItemAllowedForRole(itemId: string, role: RoleType): boolean {
  return roleSidebarItems[role].has(itemId);
}

export function hrefForSidebarItem(itemId: string, role?: RoleType): string | null {
  if (role && !isSidebarItemAllowedForRole(itemId, role)) {
    return null;
  }
  return sidebarHrefMap[itemId] ?? null;
}
