import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type UserRole = 'admin' | 'user' | 'manager' | 'auditor';

export interface Project {
  projectId: string;
  projectName: string;
  role?: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
  companyId: string;
  companyName: string;
  assignedProjects: Project[];
  activeProjectId: string;
  token?: string;
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
  token: string | null;
  companyId: string;
  companyName: string;
  activeProjectId: string;
  assignedProjects: Project[];
  permissions: Permissions;
  login: (email: string, password: string, role?: UserRole, targetCompanyId?: string) => Promise<void>;
  logout: () => void;
  hasPermission: (permission: keyof Permissions) => boolean;
  switchProject: (projectId: string) => void;
  switchCompany: (companyId: string, companyName?: string) => void;
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
  manager: {
    canUploadInvoices: true,
    canViewInvoices: true,
    canEditInvoices: true,
    canDeleteInvoices: false,
    canViewReports: true,
    canExportData: true,
    canManageUsers: false,
    canViewAnomalies: true,
    canResolveAnomalies: true,
    canAccessSettings: false,
    canChatWithVerifin: true,
    canViewDashboard: true,
    canViewVendors: true,
  },
  auditor: {
    canUploadInvoices: false,
    canViewInvoices: true,
    canEditInvoices: false,
    canDeleteInvoices: false,
    canViewReports: true,
    canExportData: true,
    canManageUsers: false,
    canViewAnomalies: true,
    canResolveAnomalies: false,
    canAccessSettings: false,
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
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    // Check if user is logged in (from localStorage)
    const savedUser = localStorage.getItem('verifin_user');
    const savedToken = localStorage.getItem('verifin_token');

    if (savedUser) {
      try {
        const parsed = JSON.parse(savedUser);
        setUser(parsed);
        if (savedToken) setToken(savedToken);
      } catch (e) {
        console.error('Error parsing saved user', e);
      }
    } else {
      // Default demo user (TechCorp Logistics)
      const defaultUser: User = {
        id: '1',
        name: 'Finance Admin',
        email: 'admin@verifin.ai',
        role: 'admin',
        companyId: 'comp_techcorp',
        companyName: 'TechCorp Logistics',
        assignedProjects: [
          { projectId: 'proj_fleet', projectName: 'Fleet Operations', role: 'admin' },
          { projectId: 'proj_supply', projectName: 'Supply Chain', role: 'admin' }
        ],
        activeProjectId: 'proj_fleet',
      };
      setUser(defaultUser);
      localStorage.setItem('verifin_user', JSON.stringify(defaultUser));
    }
  }, []);

  const login = async (email: string, password: string, role: UserRole = 'admin', targetCompanyId?: string) => {
    try {
      // Call Node.js Backend auth
      const response = await fetch('http://localhost:5000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.user) {
          const u: User = {
            id: data.user.id || data.user._id,
            name: data.user.username || email.split('@')[0],
            email: data.user.email,
            role: data.user.role || role,
            companyId: data.user.companyId || targetCompanyId || 'comp_techcorp',
            companyName: data.user.companyName || 'TechCorp Logistics',
            assignedProjects: data.user.assignedProjects || [{ projectId: 'proj_fleet', projectName: 'Fleet Operations' }],
            activeProjectId: data.user.activeProjectId || 'proj_fleet',
            token: data.token
          };
          setUser(u);
          setToken(data.token);
          localStorage.setItem('verifin_user', JSON.stringify(u));
          localStorage.setItem('verifin_token', data.token);
          return;
        }
      }
    } catch (e) {
      console.warn('Backend login endpoint unavailable, using simulated tenant login', e);
    }

    // Fallback local tenant login
    const compId = targetCompanyId || (email.includes('global') ? 'comp_globalretail' : 'comp_techcorp');
    const compName = compId === 'comp_globalretail' ? 'Global Retail Corp' : 'TechCorp Logistics';
    
    const fallbackUser: User = {
      id: Date.now().toString(),
      name: email.split('@')[0],
      email: email,
      role: role,
      companyId: compId,
      companyName: compName,
      assignedProjects: [
        { projectId: 'proj_fleet', projectName: 'Fleet Operations', role },
        { projectId: 'proj_procure', projectName: 'Store Procurement', role }
      ],
      activeProjectId: 'proj_fleet'
    };
    setUser(fallbackUser);
    localStorage.setItem('verifin_user', JSON.stringify(fallbackUser));
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('verifin_user');
    localStorage.removeItem('verifin_token');
  };

  const switchProject = (projectId: string) => {
    if (!user) return;
    const updated = { ...user, activeProjectId: projectId };
    setUser(updated);
    localStorage.setItem('verifin_user', JSON.stringify(updated));
  };

  const switchCompany = (companyId: string, companyName?: string) => {
    if (!user) return;
    const updated = {
      ...user,
      companyId,
      companyName: companyName || companyId
    };
    setUser(updated);
    localStorage.setItem('verifin_user', JSON.stringify(updated));
  };

  const permissions = user ? (rolePermissions[user.role] || rolePermissions.user) : rolePermissions.user;

  const hasPermission = (permission: keyof Permissions): boolean => {
    return permissions[permission] ?? false;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token: token || user?.token || null,
        companyId: user?.companyId || 'comp_techcorp',
        companyName: user?.companyName || 'TechCorp Logistics',
        activeProjectId: user?.activeProjectId || 'proj_fleet',
        assignedProjects: user?.assignedProjects || [],
        permissions,
        login,
        logout,
        hasPermission,
        switchProject,
        switchCompany,
      }}
    >
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
