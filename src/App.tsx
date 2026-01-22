import { useEffect, useRef, useState } from "react";
import { Moon, Sun, Gamepad2, Github, Mail, MapPin, Calendar } from "lucide-react";

type Game = {
  title: string;
  genre: string[];
  style: string;
  studio: string;
  platforms: string[];
};

type ReleaseGroup = {
  date: string;
  displayDate: string;
  games: Game[];
};

const App = () => {
  const [timeline, setTimeline] = useState<ReleaseGroup[]>([]);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const getThemeByTime = () => {
    const hour = new Date().getHours();
    return hour >= 18 ? "dark" : "light";
  };

  const getInitialTheme = () => {
    if (typeof window === "undefined") {
      return "light";
    }
    const savedTheme = window.localStorage.getItem("theme");
    if (savedTheme === "light" || savedTheme === "dark" || savedTheme === "auto") {
      return savedTheme;
    }
    return getThemeByTime();
  };

  // Initialize theme based on saved preference or local time
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    const applyTheme = () => {
      const effectiveTheme = theme === "auto" ? getThemeByTime() : theme;
      document.documentElement.setAttribute("data-theme", effectiveTheme);
    };

    applyTheme();

    if (typeof window !== "undefined") {
      window.localStorage.setItem("theme", theme);
    }

    if (theme !== "auto") {
      return;
    }

    const intervalId = window.setInterval(applyTheme, 60 * 1000);
    return () => window.clearInterval(intervalId);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => {
      if (prev === "light") return "dark";
      if (prev === "dark") return "auto";
      return "light";
    });
  };

  useEffect(() => {
    let active = true;

    const loadData = async () => {
      try {
        const indexResponse = await fetch("/data/gamerelase/index.json");
        if (!indexResponse.ok) {
          throw new Error("Failed to load release index.");
        }
        const dataFiles: string[] = await indexResponse.json();

        const requests = dataFiles.map(async (file) => {
          const response = await fetch(`/data/gamerelase/${file}`);
          if (!response.ok) {
            throw new Error(`Failed to load ${file}`);
          }
          return response.json();
        });

        const entries = await Promise.all(requests);
        const grouped = new Map<string, ReleaseGroup>();

        entries.forEach((entry) => {
          const current: ReleaseGroup = grouped.get(entry.date) ?? {
            date: entry.date,
            displayDate: entry.displayDate || entry.date,
            games: [] as Game[],
          };
          entry.games.forEach((game: Game) => current.games.push(game));
          grouped.set(entry.date, current);
        });

        const sorted = Array.from(grouped.values()).sort(
          (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
        );

        if (active) {
          setTimeline(sorted);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load timeline.");
        }
      }
    };

    loadData();

    return () => {
      active = false;
    };
  }, []);

  const scrollToToday = () => {
    const scrollEl = scrollRef.current;
    if (!scrollEl || !timeline.length) {
      return;
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    let closestIndex = 0;
    let minDiff = Number.POSITIVE_INFINITY;

    timeline.forEach((item, index) => {
      const diff = Math.abs(new Date(item.date).getTime() - today.getTime());
      if (diff < minDiff) {
        minDiff = diff;
        closestIndex = index;
      }
    });

    const target = scrollEl.querySelector<HTMLElement>(
      `[data-date="${timeline[closestIndex].date}"]`
    );

    if (!target) {
      return;
    }

    requestAnimationFrame(() => {
      // Offset calculation for centered view
      const offset =
        target.offsetTop - scrollEl.clientHeight / 2 + target.clientHeight / 2;
      scrollEl.scrollTo({ top: Math.max(offset, 0), behavior: "smooth" });
    });
  };

  useEffect(() => {
    scrollToToday();
  }, [timeline]);

  return (
    <>
      <nav className="navbar">
        <div className="nav-content">
          <div className="nav-brand-group">
            <Gamepad2 className="brand-icon" size={24} strokeWidth={1.5} />
            <span className="nav-brand">Wang Qizhi</span>
          </div>
          <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
            {theme === "light" ? (
              <Moon size={20} />
            ) : theme === "dark" ? (
              <Sun size={20} />
            ) : (
              <span aria-hidden="true">A</span>
            )}
          </button>
        </div>
      </nav>
      <div className="page">
        <header>
          <div>
            <h1 className="title">Wang Qizhi</h1>
          <p className="intro">
            Indie game fan, timeline builder, and front-end tinkerer. I like calm
            interfaces with bold stories. This page is a living schedule of the games I am
            watching from the past into the far horizon.
          </p>
        </div>
        <div className="pill-row">
          <a className="pill" href="mailto:wangqizhi1987@gmail.com">
            <Mail size={16} />
            wangqizhi1987@gmail.com
          </a>
          <a className="pill" href="https://github.com/">
            <Github size={16} />
            github.com
          </a>
          <span className="pill">
            <MapPin size={16} />
            Based in Shanghai
          </span>
        </div>
      </header>

      <section className="timeline-shell">
        <div className="section-head">
          <div className="section-header-content">
            <h2 className="section-title">Game Release Timeline</h2>
            <p className="section-hint">Scroll up for past releases, down for future dates.</p>
          </div>
          <button className="today-btn" onClick={scrollToToday} title="Jump to Today">
            <Calendar size={18} />
            <span>Today</span>
          </button>
        </div>
        <div className="timeline-scroll" ref={scrollRef}>
          <div className="timeline">
            {error ? (
              <div className="timeline-item static">
                <div className="timeline-dot" />
                <div className="timeline-date">Data error</div>
                <div className="game-card">{error}</div>
              </div>
            ) : timeline.length ? (
              timeline.map((group, index) => (
                <div
                  key={group.date}
                  className="timeline-item"
                  style={{ animationDelay: `${index * 0.12}s` }}
                  data-date={group.date}
                >
                  <div className="timeline-dot" />
                  <div className="timeline-date">{group.displayDate}</div>
                  <div className="game-card-wrapper">
                    {group.games.map((game) => (
                      <div key={game.title} className="game-card">
                        <h3>{game.title}</h3>
                        <p>{game.style}</p>
                        <div className="game-meta">
                          {game.studio} · {game.platforms.join(", ")}
                        </div>
                        <div className="tag-row">
                          {game.genre.map((tag) => (
                            <span key={tag} className="tag">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <div className="timeline-item static">
                <div className="timeline-dot" />
                <div className="timeline-date">Loading</div>
                <div className="game-card">Fetching release data...</div>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
    </>
  );
};

export default App;
