import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [workspace, setWorkspace] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, password, workspace);
      }
      navigate("/chat");
    } catch (err) {
      setError(err.message || "An error occurred");
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-gray-100">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-md border">
        <h1 className="text-3xl font-bold mb-6 text-center text-blue-700 tracking-tight">Paperly</h1>
        <div className="flex mb-6">
          <button
            className={`flex-1 pb-2 ${isLogin ? "border-b-2 border-blue-500 font-semibold text-blue-700" : "text-gray-500 border-b"}`}
            onClick={() => setIsLogin(true)}
          >
            Login
          </button>
          <button
            className={`flex-1 pb-2 ${!isLogin ? "border-b-2 border-blue-500 font-semibold text-blue-700" : "text-gray-500 border-b"}`}
            onClick={() => setIsLogin(false)}
          >
            Register
          </button>
        </div>
        
        {error && <p className="text-red-600 text-sm mb-4 bg-red-50 p-2 rounded">{error}</p>}
        
        <form onSubmit={handleSubmit} className="flex flex-col space-y-4">
          <input
            type="email"
            placeholder="Email address"
            className="border p-2.5 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password (min 8 chars)"
            className="border p-2.5 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
          {!isLogin && (
            <input
              type="text"
              placeholder="Workspace Name"
              className="border p-2.5 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={workspace}
              onChange={(e) => setWorkspace(e.target.value)}
              required
            />
          )}
          <button type="submit" className="bg-blue-600 text-white font-medium p-2.5 rounded hover:bg-blue-700 transition-colors mt-2">
            {isLogin ? "Sign In" : "Create Account"}
          </button>
        </form>
      </div>
    </div>
  );
}
