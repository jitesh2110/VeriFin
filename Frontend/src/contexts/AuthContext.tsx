import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type UserRole = 'admin' | 'user';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
}

export interface Permissions {
  canUploadInvoices: boolean;
  canViewInvoices: boolean;
  canEditInvoices: boolean;
  canDeleteInvoices: boolean;
  canViewReports: boolean;
  canExportData: boolean;
  canManageUsers: boolean;
  canViewAnomalies: boolean;
  canResolveAnomalies: boolean;
  canAccessSettings: boolean;
  canChatWithVerifin: boolean;
  canViewDashboard: boolean;
  canViewVendors: boolean;
}

interface AuthContextType {
  user: User | null;
  permissions: Permissions;
  login: (email: string, password: string, role: UserRole) => void;
  logout: () => void;
  hasPermission: (permission: keyof Permissions) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Role-based permissions mapping
const rolePermissions: Record<UserRole, Permissions> = {
  admin: {
    canUploadInvoices: true,
    canViewInvoices: true,
    canEditInvoices: true,
    canDeleteInvoices: true,
    canViewReports: true,
    canExportData: true,
    canManageUsers: true,
    canViewAnomalies: true,
    canResolveAnomalies: true,
    canAccessSettings: true,
    canChatWithVerifin: true,
    canViewDashboard: true,
    canViewVendors: true,
  },
  user: {
    canUploadInvoices: true,
    canViewInvoices: true,
    canEditInvoices: false,
    canDeleteInvoices: false,
    canViewReports: false,
    canExportData: true,
    canManageUsers: false,
    canViewAnomalies: false,
    canResolveAnomalies: false,
    canAccessSettings: false,
    canChatWithVerifin: false,
    canViewDashboard: false,
    canViewVendors: false,
  },
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // Check if user is logged in (from localStorage)
    const savedUser = localStorage.getItem('verifin_user') || localStorage.getItem('fintel_user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    } else {
      // Default user for demo (Admin)
      const defaultUser: User = {
        id: '1',
        name: 'Finance Admin',
        email: 'admin@verifin.ai',
        role: 'admin',
      };
      setUser(defaultUser);
      localStorage.setItem('verifin_user', JSON.stringify(defaultUser));
    }
  }, []);

  const login = (email: string, password: string, role: UserRole) => {
    // Mock login - in production, this would call an API
    const newUser: User = {
      id: Date.now().toString(),
      name: getRoleName(role),
      email: email,
      role: role,
    };
    setUser(newUser);
    localStorage.setItem('verifin_user', JSON.stringify(newUser));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('verifin_user');
    localStorage.removeItem('fintel_user');
  };

  const permissions = user ? rolePermissions[user.role] : rolePermissions.user;

  const hasPermission = (permission: keyof Permissions): boolean => {
    return permissions[permission];
  };

  return (
    <AuthContext.Provider value={{ user, permissions, login, logout, hasPermission }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

function getRoleName(role: UserRole): string {
  const roleNames: Record<UserRole, string> = {
    admin: 'Admin',
    user: 'User',
  };
  return roleNames[role];
}
