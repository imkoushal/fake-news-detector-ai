import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE, getAuthHeaders } from '../lib/api';

interface User {
  id: number;
  name: string;
  email: string;
  avatar_url?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
  showAuthModal: boolean;
  setShowAuthModal: (show: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('verify_token'));
  const [isLoading, setIsLoading] = useState(true);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    async function checkSession() {
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
          headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('Session invalid');
        const userData = await res.json();
        setUser(userData);
      } catch (err) {
        setToken(null);
        localStorage.removeItem('verify_token');
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }
    checkSession();
  }, [token]);

  const login = (newToken: string, newUser: User) => {
    localStorage.setItem('verify_token', newToken);
    setToken(newToken);
    setUser(newUser);
    setShowAuthModal(false);
    navigate('/dashboard');
  };

  const logout = async () => {
    if (token) {
      try {
        await fetch(`${API_BASE}/api/v1/auth/logout`, {
          method: 'POST',
          headers: getAuthHeaders()
        });
      } catch (e) {
        console.error(e);
      }
    }
    localStorage.removeItem('verify_token');
    setToken(null);
    setUser(null);
    navigate('/');
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, token, login, logout, showAuthModal, setShowAuthModal }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

