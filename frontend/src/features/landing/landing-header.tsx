import { ArrowRight, UserRound } from "lucide-react";
import styles from "./landing.module.css";

export function LandingHeader({
  authenticated,
  loading,
  onEnter,
}: {
  authenticated: boolean;
  loading: boolean;
  onEnter: () => void;
}): React.JSX.Element {
  return (
    <header className={styles.header}>
      <a href="#inicio" className={styles.brand} aria-label="ASGARD, inicio">
        <svg viewBox="0 0 64 64" aria-hidden="true">
          <defs>
            <linearGradient id="asgard-mark" x1="0" y1="1" x2="1" y2="0">
              <stop stopColor="#26a653" />
              <stop offset="1" stopColor="#064f3c" />
            </linearGradient>
          </defs>
          <path
            d="M5 55 29 8Q33 1 38 8L43 18 22 58Q21 61 17 61H8Q2 61 5 55Z"
            fill="url(#asgard-mark)"
          />
          <path
            d="m41 22 8 17-19 5ZM33 48l18-5 9 13q2 5-4 5h-9q-3 0-5-4Z"
            fill="#086147"
          />
          <path d="m38 15 5 10-8 16-8 2Z" fill="#a3d4af" />
        </svg>
        <span>ASGARD</span>
      </a>
      <nav className={styles.nav} aria-label="Navegación principal">
        <a href="#inicio" aria-current="page">
          Inicio
        </a>
        <a href="#solucion">Solución</a>
        <a href="#proceso">Proceso</a>
        <a href="#beneficios">Beneficios</a>
        <a href="#contacto">Contacto</a>
      </nav>
      <button className={styles.primary} onClick={onEnter} disabled={loading}>
        <UserRound aria-hidden="true" />
        {authenticated ? "Ir al panel" : "Ingresar"}
        <ArrowRight aria-hidden="true" />
      </button>
    </header>
  );
}
