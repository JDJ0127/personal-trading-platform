import { navItems, type NavItem } from "../data/mockData";

type SidebarProps = {
  activeItem: NavItem;
  onSelect: (item: NavItem) => void;
};

export function Sidebar({ activeItem, onSelect }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-title">板块目录</div>
      <nav className="nav-list" aria-label="平台板块目录">
        {navItems.map((item) => (
          <button
            className={`nav-item ${activeItem === item ? "active" : ""}`}
            key={item}
            type="button"
            onClick={() => onSelect(item)}
          >
            <span>{item}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
