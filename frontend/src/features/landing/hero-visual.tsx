import Image from "next/image";
import {
  BookOpen,
  Check,
  Lightbulb,
  ChartNoAxesColumnIncreasing,
} from "lucide-react";
import styles from "./landing.module.css";

export function HeroVisual(): React.JSX.Element {
  return (
    <div className={styles.visual}>
      <div className={styles.decorations} aria-hidden="true">
        <div className={`${styles.blob} ${styles.blobOne}`} />
        <div className={`${styles.blob} ${styles.blobTwo}`} />
        <div className={`${styles.blob} ${styles.blobThree}`} />
        <svg className={styles.flowLine} viewBox="0 0 760 700" fill="none">
          <path
            d="M150 480C-30 310 12 15 214 181S750 229 734 356 100 495 274 620 730 688 552 564"
            stroke="currentColor"
            strokeWidth="1.8"
          />
        </svg>
        {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
          <i
            className={styles.particle}
            key={n}
            style={{
              left: `${[9, 12, 6, 15, 88, 96, 72, 31, 67][n]}%`,
              top: `${[6, 11, 48, 91, 9, 72, 24, 18, 79][n]}%`,
              animationDelay: `${n * -1.7}s`,
            }}
          />
        ))}
        <svg className={styles.accents} viewBox="0 0 100 100">
          <path
            d="m22 46 15-34M51 63l25-30M65 82l25-14"
            fill="none"
            stroke="currentColor"
            strokeWidth="9"
            strokeLinecap="round"
          />
        </svg>
        <div className={styles.dotGrid} />
      </div>
      <p className={`${styles.handwriting} ${styles.ideas}`} aria-hidden="true">
        Ideas
        <br />
        que transforman
        <br />
        la formación
      </p>
      <div
        className={`${styles.floatingCard} ${styles.bookCard}`}
        aria-hidden="true"
      >
        <BookOpen />
      </div>
      <div
        className={`${styles.floatingCard} ${styles.checklist}`}
        aria-label="Un flujo organizado"
      >
        {["Programa", "Proyecto", "Planeación", "Guías de aprendizaje"].map(
          (label) => (
            <div key={label}>
              <Check aria-hidden="true" />
              <span>{label}</span>
            </div>
          ),
        )}
      </div>
      <div className={`${styles.floatingCard} ${styles.ideaCard}`}>
        <Lightbulb aria-hidden="true" />
        <span>
          Orientación
          <br />
          en cada paso
        </span>
      </div>
      <Image
        className={styles.instructor}
        src="/landing/asgard-instructor.png"
        alt="Instructora del SENA sonriente, con gafas y bata blanca, sosteniendo cuadernos y una tableta"
        width={1181}
        height={1332}
        sizes="(max-width: 767px) 94vw, 46vw"
        priority
      />
      <div className={`${styles.floatingCard} ${styles.impactCard}`}>
        <ChartNoAxesColumnIncreasing aria-hidden="true" />
        <span>
          Formación
          <br />
          con impacto
        </span>
      </div>
      <p
        className={`${styles.handwriting} ${styles.footnote}`}
        aria-hidden="true"
      >
        Instructores
        <br />
        que dejan huella
      </p>
    </div>
  );
}
