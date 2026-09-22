"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, CirclePlay, Sprout } from "lucide-react";
import { useAuth } from "@/features/auth/auth-context";
import { LoginDialog } from "@/features/auth/login-dialog";
import { ForceChangePasswordDialog } from "@/features/auth/force-change-password-dialog";
import { LandingHeader } from "./landing-header";
import { HeroVisual } from "./hero-visual";
import { HeroFeatureStrip } from "./hero-feature-strip";
import styles from "./landing.module.css";

export function LandingPage({
  className = "",
}: {
  className?: string;
}): React.JSX.Element {
  const { isAuthenticated, isLoading, user, refreshUser } = useAuth();
  const router = useRouter();
  const [loginOpen, setLoginOpen] = useState(false);
  const [enterRequested, setEnterRequested] = useState(false);

  useEffect(() => {
    if (
      enterRequested &&
      isAuthenticated &&
      user &&
      !user.debe_cambiar_password
    ) {
      router.push("/dashboard");
    }
  }, [enterRequested, isAuthenticated, user, router]);

  function enter(): void {
    setEnterRequested(true);
    if (!isAuthenticated) setLoginOpen(true);
  }

  function scrollToProcess(event: React.MouseEvent<HTMLAnchorElement>): void {
    event.preventDefault();
    document.getElementById("proceso")?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
    });
    window.history.replaceState(null, "", "#proceso");
  }

  return (
    <div className={`${styles.landing} ${className}`} id="inicio">
      <a className={styles.skipLink} href="#contenido">
        Saltar al contenido
      </a>
      <LandingHeader
        authenticated={isAuthenticated}
        loading={isLoading}
        onEnter={enter}
      />
      <main id="contenido">
        <section className={styles.hero} aria-labelledby="hero-title">
          <div className={styles.copy}>
            <p className={styles.eyebrow}>Asistente pedagógico inteligente</p>
            <h1 id="hero-title">
              Construye planeaciones
              <br className={styles.desktopBreak} /> pedagógicas con claridad
              <br className={styles.desktopBreak} />{" "}
              <span>y acompañamiento</span>
            </h1>
            <p className={styles.description} id="solucion">
              ASGARD ayuda a los instructores del SENA a organizar programa,
              proyecto y planeación en un flujo guiado, visual y estructurado.
            </p>
            <div className={styles.actions}>
              <button
                className={styles.primary}
                onClick={enter}
                disabled={isLoading}
              >
                Comenzar ahora <ArrowRight aria-hidden="true" />
              </button>
              <a
                className={styles.secondary}
                href="#proceso"
                onClick={scrollToProcess}
              >
                <CirclePlay aria-hidden="true" /> Ver cómo funciona
              </a>
            </div>
            <p className={styles.claim} id="beneficios">
              <Sprout aria-hidden="true" />
              <span>
                Más tiempo para enseñar, mayor impacto en el aprendizaje
              </span>
            </p>
          </div>
          <HeroVisual />
        </section>
        <HeroFeatureStrip />
      </main>
      <footer className={styles.contact} id="contacto">
        <span>ASGARD · Acompañamiento pedagógico</span>
        <p>
          Para recibir orientación, contacta a tu líder de equipo ejecutor o al
          administrador de tu centro de formación.
        </p>
      </footer>
      <LoginDialog
        isOpen={loginOpen && !isAuthenticated}
        onClose={() => setLoginOpen(false)}
      />
      <ForceChangePasswordDialog
        isOpen={isAuthenticated && !!user?.debe_cambiar_password}
        onPasswordChanged={() => void refreshUser()}
      />
    </div>
  );
}
