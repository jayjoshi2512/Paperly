import { useState } from "react";
import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useStreamingChat } from "../hooks/useStreamingChat";
import { MessageSquare, FileText, BarChart2, LogOut, Plus, Trash2, AlertTriangle, X } from "lucide-react";
import styles from "./Layout.module.css";

export default function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const chatState = useStreamingChat();
  const [sessionToDelete, setSessionToDelete] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const isActive = (path) => location.pathname.startsWith(path);

  const confirmDelete = async () => {
    if (!sessionToDelete) return;
    try {
      await chatState.deleteSession(sessionToDelete.id);
      setSessionToDelete(null);
      setDeleteError(null);
    } catch (err) {
      setDeleteError(err.message || "Failed to delete");
    }
  };

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
              <div key={s.id} className={`${styles.sessionItemWrapper} ${chatState.currentSessionId === s.id ? styles.active : ""}`}>
                <button 
                  className={styles.sessionItem}
                  onClick={() => {
                    chatState.switchSession(s.id);
                    if (!isActive("/chat")) navigate("/chat");
                  }}
                  title={s.title}
                >
                  {s.title}
                </button>
                <button 
                  className={styles.sessionDeleteBtn}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSessionToDelete(s);
                  }}
                  title="Delete Chat"
                >
                  <Trash2 size={12} />
                </button>
              </div>
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

      {sessionToDelete && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>
                <AlertTriangle size={20} className={styles.modalIcon} />
                Delete Chat Session
              </div>
              <button onClick={() => setSessionToDelete(null)} className={styles.closeBtn}>
                <X size={18} />
              </button>
            </div>
            <div className={styles.modalBody}>
              Are you sure you want to delete this chat? This action cannot be undone.
              {deleteError && <div className={styles.modalError}>{deleteError}</div>}
            </div>
            <div className={styles.modalFooter}>
              <button onClick={() => setSessionToDelete(null)} className={styles.cancelBtn}>Cancel</button>
              <button onClick={confirmDelete} className={styles.confirmBtn}>Delete Chat</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
