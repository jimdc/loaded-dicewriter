import { Outlet } from "react-router-dom";
import "../styles/shell.css";
import { DieMark } from "./DieMark";

/**
 * Static single-page shell: brand + main content.
 * Gallery is frozen JSON — no backend status or live generation required.
 */
export function AppShell() {
  return (
    <div className="app-shell app-shell--single">
      <header className="top-bar" aria-label="App">
        <div className="top-bar__brand">
          <span className="top-bar__mark" aria-hidden="true">
            <DieMark size={14} />
          </span>
          <span className="top-bar__title">loaded-dicewriter</span>
        </div>
      </header>

      <main className="main">
        <div className="main__inner">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
