export interface CoordinacionSimple {
  id: string;
  codigo: string;
  nombre: string;
}

export interface EspecialidadSimple {
  id: string;
  codigo: string;
  nombre: string;
}

export interface ProgramaSimple {
  id: string;
  codigo_programa: string;
  nombre_programa: string;
  version_programa?: string | null;
}

export interface User {
  id: string;
  email: string;
  nombre: string;
  apellido: string;
  telefono?: string | null;
  area?: string | null;
  estado: string;
  activo: boolean;
  debe_cambiar_password: boolean;
  ultimo_acceso?: string | null;
  roles: string[];
  coordinacion?: CoordinacionSimple | null;
  especialidad?: EspecialidadSimple | null;
  programas_autorizados?: ProgramaSimple[];
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}
