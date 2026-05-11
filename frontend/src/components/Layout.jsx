import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { MessageSquare, FileText, BarChart2, LogOut } from "lucide-react";

export default function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const navItemClass = (path) => {
    const isActive = location.pathname.startsWith(path);
    return `flex items-center space-x-3 p-3 rounded-lg transition-colors ${isActive ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'}`;
  };

  return (
    <div className="flex h-screen bg-white">
      <aside className="w-64 bg-gray-50 border-r flex flex-col">
        <div className="p-6">
          <h1 className="font-bold text-2xl text-blue-700 tracking-tight">Paperly</h1>
        </div>
        <nav className="flex-1 px-4 space-y-1">
          <Link to="/chat" className={navItemClass("/chat")}>
            <MessageSquare size={20} />
            <span>Chat Assistant</span>
          </Link>
          <Link to="/documents" className={navItemClass("/documents")}>
            <FileText size={20} />
            <span>Knowledge Base</span>
          </Link>
          <Link to="/eval" className={navItemClass("/eval")}>
            <BarChart2 size={20} />
            <span>Dashboard</span>
          </Link>
        </nav>
        <div className="p-4 border-t">
          <button onClick={handleLogout} className="flex items-center space-x-3 text-gray-600 hover:text-red-600 w-full p-3 rounded-lg hover:bg-red-50 transition-colors">
            <LogOut size={20} />
            <span>Logout</span>
          </button>
        </div>
      </aside>
      <main className="flex-1 flex flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
