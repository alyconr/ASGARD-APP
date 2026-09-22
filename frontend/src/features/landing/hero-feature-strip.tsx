import {
  FileText,
  FolderOpen,
  CalendarDays,
  BookOpen,
  ChartNoAxesColumnIncreasing,
} from "lucide-react";
import styles from "./landing.module.css";

const features = [
  { title: "Programa", description: "Organiza tu programa", icon: FileText },
  {
    title: "Proyecto",
    description: "Estructura con facilidad",
    icon: FolderOpen,
  },
  {
    title: "Planeación",
    description: "Diseña paso a paso",
    icon: CalendarDays,
  },
  {
    title: "Guías",
    description: "Genera guías de aprendizaje",
    icon: BookOpen,
  },
  {
    title: "Trazabilidad",
    description: "Haz seguimiento al avance",
    icon: ChartNoAxesColumnIncreasing,
  },
];

export function HeroFeatureStrip(): React.JSX.Element {
  return (
    <section
      className={styles.featureStrip}
      id="proceso"
      aria-label="Proceso y capacidades de ASGARD"
    >
      <ul>
        {features.map(({ title, description, icon: Icon }) => (
          <li key={title}>
            <Icon aria-hidden="true" />
            <div>
              <h2>{title}</h2>
              <p>{description}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
