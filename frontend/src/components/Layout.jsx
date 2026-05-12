import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useStreamingChat } from "../hooks/useStreamingChat";
import { MessageSquare, FileText, BarChart2, LogOut, Plus } from "lucide-react";
import styles from "./Layout.module.css";

export default function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const chatState = useStreamingChat();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const isActive = (path) => location.pathname.startsWith(path);

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <div className={styles.brandIcon}>P</div>
          <span className={styles.brandName}>Paperly</span>
        </div>

        <nav className={styles.nav}>
          <Link
            to="/chat"
            className={`${styles.navItem} ${isActive("/chat") ? styles.active : ""}`}
          >
            <MessageSquare className={styles.navIcon} />
            <span>Chat</span>
          </Link>
          <Link
            to="/documents"
            className={`${styles.navItem} ${isActive("/documents") ? styles.active : ""}`}
          >
            <FileText className={styles.navIcon} />
            <span>Data Sources</span>
          </Link>
          <Link
            to="/eval"
            className={`${styles.navItem} ${isActive("/eval") ? styles.active : ""}`}
          >
            <BarChart2 className={styles.navIcon} />
            <span>Insights</span>
          </Link>
          
          <div className={styles.divider} />
          
          <button 
            className={styles.newChatBtn} 
            onClick={() => {
              chatState.startNewSession();
              if (!isActive("/chat")) navigate("/chat");
            }}
          >
            <Plus size={16} /> New Chat
          </button>
          
          <div className={styles.sessionList}>
            {chatState.sessions.map(s => (
              <button 
                key={s.id} 
                className={`${styles.sessionItem} ${chatState.currentSessionId === s.id ? styles.active : ""}`}
                onClick={() => {
                  chatState.switchSession(s.id);
                  if (!isActive("/chat")) navigate("/chat");
                }}
                title={s.title}
              >
                {s.title}
              </button>
            ))}
          </div>
        </nav>

        <div className={styles.sidebarFooter}>
          <button onClick={handleLogout} className={styles.logoutBtn}>
            <LogOut className={styles.navIcon} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      <main className={styles.main}>
        <Outlet context={chatState} />
      </main>
    </div>
  );
}
