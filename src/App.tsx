import { useEffect, useState } from "react";
import { DashboardSections } from "./components/DashboardSections";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { navItems, type NavItem } from "./data/mockData";

export default function App() {
  const [activeItem, setActiveItem] = useState<NavItem>(navItems[0]);

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0 });
  }, [activeItem]);

  return (
    <div className="app-shell">
      <TopBar />
      <div className="workspace">
        <Sidebar activeItem={activeItem} onSelect={setActiveItem} />
        <main className="content-panel">
          <DashboardSections activeItem={activeItem} />
        </main>
      </div>
    </div>
  );
}
