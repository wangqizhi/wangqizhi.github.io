import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Virtuoso, type VirtuosoHandle } from "react-virtuoso";
import { Moon, Sun, Gamepad2, Github, Mail, MapPin, Calendar, Languages, Tv, Clock } from "lucide-react";

const PLATFORM_FILTERS = [
  { key: "PC", label: "PC", className: "platform-pc" },
  { key: "NS", label: "NS", className: "platform-ns" },
  { key: "NS2", label: "NS2", className: "platform-ns" },
  { key: "PS4", label: "PS4", className: "platform-ps" },
  { key: "PS5", label: "PS5", className: "platform-ps" },
  { key: "Xbox One", label: "XB1", className: "platform-xbox" },
  { key: "Xbox Series X|S", label: "XSX", className: "platform-xbox" },
] as const;

type PlatformKey = (typeof PLATFORM_FILTERS)[number]["key"];

type Game = {
  title: string;
  genre: string[];
  style: string;
  studio: string;
  platforms: string[];
};

type Showcase = {
  title: string;
  title_en?: string;
  displayDate?: string;
  genre: string[];
  style: string;
  style_en?: string;
};

type ShowcaseGroup = {
  date: string;
  displayDate: string;
  showcases: Showcase[];
};

type ReleaseGroup = {
  date: string;
  displayDate: string;
  games: Game[];
  showcases?: Showcase[];
};

type YearPayload = ReleaseGroup[] | { year?: string; releases?: ReleaseGroup[] };

type GameTranslation = {
  zh: string;
  en: string;
  jp: string;
};

type UiStrings = typeof defaultUiStrings & {
  genreTypes?: Record<string, string>;
};

const defaultUiStrings = {
  timelineTitle: "Game Release Timeline",
  timelineHint: "Scroll up for past releases, down for future dates.",
  today: "Today",
  loadingPrevYear: "Loading previous year...",
  loadingNextYear: "Loading next year...",
  clickToLoadPrevYear: "Click to load previous year",
  noMoreData: "No more data.",
  dataError: "Data error",
  loading: "Loading",
  fetchingData: "Fetching release data...",
  studio: "Studio:",
  platforms: "Platforms:",
  genres: "Genres:",
  viewDetails: "View game details",
};

type UiKey = keyof typeof defaultUiStrings;

type TimelineGroupItemProps = {
  group: ReleaseGroup;
  selectedPlatforms: Set<PlatformKey>;
  matchesPlatformFilter: (platforms: string[]) => boolean;
  getTranslatedGameName: (title: string) => string;
  getTranslatedGenre: (genre: string) => string;
  getPlatformClass: (platform: string) => string;
  viewDetailsLabel: string;
  animationsEnabled: boolean;
  animationDelay?: number;
  onSelectGame: (game: Game) => void;
  showOnlyShowcase: boolean;
  language: "en" | "zh";
};

const TimelineGroupItem = memo(function TimelineGroupItem({
  group,
  selectedPlatforms,
  matchesPlatformFilter,
  getTranslatedGameName,
  getTranslatedGenre,
  getPlatformClass,
  viewDetailsLabel,
  animationsEnabled,
  animationDelay,
  onSelectGame,
  showOnlyShowcase,
  language,
}: TimelineGroupItemProps) {
  const filteredGames = useMemo(() => {
    if (showOnlyShowcase) {
      return [];
    }
    if (selectedPlatforms.size === 0) {
      return group.games;
    }
    return group.games.filter((game) => matchesPlatformFilter(game.platforms));
  }, [group.games, matchesPlatformFilter, selectedPlatforms, showOnlyShowcase]);

  const showcases = group.showcases ?? [];
  const hasContent = filteredGames.length > 0 || showcases.length > 0;

  // 转换 displayDate 从 UTC+8 到本地时区
  const localDisplayDate = convertUTC8ToLocal(group.displayDate);

  if (!hasContent) {
    return (
      <div
        key={group.date}
        className="timeline-item-placeholder"
        aria-hidden="true"
      />
    );
  }

  return (
    <div
      key={group.date}
      className="timeline-item"
      style={
        animationsEnabled && typeof animationDelay === "number"
          ? { animationDelay: `${animationDelay}s` }
          : undefined
      }
      data-date={group.date}
    >
      <div className="timeline-dot" />
      <div className="timeline-date">{localDisplayDate}</div>
      <div className="game-card-wrapper">
        {/* Showcase 卡片 */}
        {showcases.map((showcase) => {
          // 根据语言选择显示的 title 和 style
          const displayTitle = language === "en" && showcase.title_en
            ? showcase.title_en
            : showcase.title;
          const displayStyle = language === "en" && showcase.style_en
            ? showcase.style_en
            : showcase.style;
          // 从 showcase 的 displayDate 转换展示时间到本地时区
          const localDisplayDate = showcase.displayDate
            ? convertUTC8ToLocal(showcase.displayDate)
            : undefined;
          const localTime = localDisplayDate
            ? localDisplayDate.split(" ")[1]
            : undefined;

          return (
            <div key={showcase.title} className="game-card showcase-card">
              <div className="game-card-header">
                <h3>{getTranslatedGameName(displayTitle)}</h3>
                {localTime && (
                  <div className="showcase-time">
                    <Clock size={14} className="showcase-time-icon" />
                    <span>{localTime}</span>
                  </div>
                )}
              </div>
              <div className="game-style-wrapper" data-tooltip={displayStyle}>
                <p className="game-style">{displayStyle}</p>
              </div>
              <div className="tag-row">
                {showcase.genre.map((tag) => (
                  <span key={tag} className="tag showcase-tag">
                    {getTranslatedGenre(tag)}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
        {/* 游戏卡片 */}
        {filteredGames.map((game) => (
          <div key={game.title} className="game-card">
            <div className="game-card-header">
              <h3>{getTranslatedGameName(game.title)}</h3>
              <button
                className="game-detail-btn"
                onClick={() => onSelectGame(game)}
                aria-label={viewDetailsLabel}
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="1" />
                  <circle cx="19" cy="12" r="1" />
                  <circle cx="5" cy="12" r="1" />
                </svg>
              </button>
            </div>
            <div className="game-style-wrapper" data-tooltip={game.style}>
              <p className="game-style">{game.style}</p>
            </div>
            <div className="game-meta">
              <span className="game-studio">{game.studio}</span>
              <div className="platform-row">
                {game.platforms.map((p) => (
                  <span key={p} className={`platform-badge ${getPlatformClass(p)}`}>
                    {p}
                  </span>
                ))}
              </div>
            </div>
            <div className="tag-row">
              {game.genre.map((tag) => (
                <span key={tag} className="tag">
                  {getTranslatedGenre(tag)}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

const getInitialLanguage = () => {
  if (typeof window === "undefined") {
    return "en" as const;
  }
  const saved = window.localStorage.getItem("language");
  return saved === "zh" || saved === "en" ? saved : "en";
};

const toLocalDayValue = (dateString: string) => {
  const [year, month, day] = dateString.split("-").map(Number);
  if (!year || !month || !day) {
    return null;
  }
  return new Date(year, month - 1, day).getTime();
};

/**
 * 将 UTC+8 时间字符串转换为浏览器本地时间
 * @param displayDate 格式 "YYYY-MM-DD HH:mm"，假定为 UTC+8 时间
 * @returns 本地时间字符串，格式 "YYYY-MM-DD HH:mm"
 */
const convertUTC8ToLocal = (displayDate: string): string => {
  // 解析 displayDate，格式 "2026-01-30 01:00"
  const match = displayDate.match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})$/);
  if (!match) {
    return displayDate; // 格式不匹配，直接返回原值
  }

  const [, yearStr, monthStr, dayStr, hourStr, minuteStr] = match;
  const year = Number(yearStr);
  const month = Number(monthStr) - 1; // JS 月份从 0 开始
  const day = Number(dayStr);
  const hour = Number(hourStr);
  const minute = Number(minuteStr);

  // 创建 UTC+8 时间对应的 UTC 时间戳
  // UTC+8 时间比 UTC 早 8 小时，所以 UTC = UTC+8 - 8小时
  const utcTimestamp = Date.UTC(year, month, day, hour - 8, minute);

  // 创建 Date 对象（会自动转换为本地时间）
  const localDate = new Date(utcTimestamp);

  // 格式化为 "YYYY-MM-DD HH:mm"
  const localYear = localDate.getFullYear();
  const localMonth = String(localDate.getMonth() + 1).padStart(2, "0");
  const localDay = String(localDate.getDate()).padStart(2, "0");
  const localHour = String(localDate.getHours()).padStart(2, "0");
  const localMinute = String(localDate.getMinutes()).padStart(2, "0");

  return `${localYear}-${localMonth}-${localDay} ${localHour}:${localMinute}`;
};

const sortGroupsByDate = (groups: ReleaseGroup[]) =>
  [...groups].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

type TimelineState = {
  data: ReleaseGroup[];
  firstItemIndex: number;
};

const INITIAL_FIRST_ITEM_INDEX = 100000;

const App = () => {
  // 将 timeline 和 firstItemIndex 合并为一个状态，确保原子更新
  // 这是修复 prepend 数据时滚动位置跳动的关键
  const [timelineState, setTimelineState] = useState<TimelineState>({
    data: [],
    firstItemIndex: INITIAL_FIRST_ITEM_INDEX,
  });
  const timeline = timelineState.data;
  const firstItemIndex = timelineState.firstItemIndex;

  const [error, setError] = useState<string | null>(null);
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [loadedYears, setLoadedYears] = useState<number[]>([]);
  const [loadingPrev, setLoadingPrev] = useState(false);
  const [loadingNext, setLoadingNext] = useState(false);
  const [canAutoLoad, setCanAutoLoad] = useState(false);
  const [animationsEnabled, setAnimationsEnabled] = useState(true);
  const [selectedGame, setSelectedGame] = useState<Game | null>(null);
  const [language, setLanguage] = useState<"en" | "zh">(getInitialLanguage);
  const [uiTranslations, setUiTranslations] = useState<Record<string, UiStrings>>({
    en: defaultUiStrings,
  });
  const [gameTranslations, setGameTranslations] = useState<Map<string, GameTranslation>>(new Map());
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<PlatformKey>>(() => {
    if (typeof window !== "undefined") {
      const saved = window.localStorage.getItem("selectedPlatforms");
      if (saved) {
        try {
          const parsed = JSON.parse(saved) as string[];
          return new Set(parsed as PlatformKey[]);
        } catch {
          // 解析失败，使用默认值
        }
      }
    }
    // 默认不选中 PC，选中其他所有平台
    const initial = new Set<PlatformKey>();
    PLATFORM_FILTERS.forEach((p) => {
      if (p.key !== "PC") {
        initial.add(p.key);
      }
    });
    return initial;
  });
  const [showOnlyShowcase, setShowOnlyShowcase] = useState(false);

  const virtuosoRef = useRef<VirtuosoHandle>(null);
  const didInitialScrollRef = useRef(false);
  const loadingPrevRef = useRef(false);
  const loadingNextRef = useRef(false);
  const timelineRef = useRef<ReleaseGroup[]>([]);
  const visibleRangeRef = useRef({ startIndex: 0, endIndex: 0 });

  const ANIMATION_STAGGER_STEP = 0.06;
  const ANIMATION_MAX_DELAY = 0.6;

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

  const toggleLanguage = () => {
    setLanguage((prev) => (prev === "en" ? "zh" : "en"));
  };

  const togglePlatform = (platform: PlatformKey) => {
    setSelectedPlatforms((prev) => {
      const next = new Set(prev);
      if (next.has(platform)) {
        next.delete(platform);
      } else {
        next.add(platform);
      }
      return next;
    });
  };

  const matchesPlatformFilter = useCallback(
    (gamePlatforms: string[]) => {
      if (selectedPlatforms.size === 0) {
        return true; // 没有选中任何平台时显示所有游戏
      }
      return gamePlatforms.some((p) => selectedPlatforms.has(p as PlatformKey));
    },
    [selectedPlatforms]
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem("language", language);
  }, [language]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem("selectedPlatforms", JSON.stringify([...selectedPlatforms]));
  }, [selectedPlatforms]);

  useEffect(() => {
    timelineRef.current = timeline;
  }, [timeline]);

  useEffect(() => {
    const loadUiTranslations = async () => {
      try {
        const response = await fetch("/data/i18n.json");
        if (response.ok) {
          const data: Record<string, UiStrings> = await response.json();
          setUiTranslations((prev) => ({ ...prev, ...data }));
        }
      } catch (err) {
        console.error("Failed to load UI translations:", err);
      }
    };
    loadUiTranslations();
  }, []);

  const t = useCallback(
    (key: UiKey) => {
      const fallback = uiTranslations.en ?? defaultUiStrings;
      const current = uiTranslations[language];
      return (current && current[key]) || fallback[key] || defaultUiStrings[key];
    },
    [language, uiTranslations]
  );

  const getTranslatedGameName = useCallback(
    (originalTitle: string): string => {
      const translation = gameTranslations.get(originalTitle);
      if (!translation) return originalTitle;
      return translation[language] || originalTitle;
    },
    [gameTranslations, language]
  );

  const getTranslatedGenre = useCallback(
    (genreName: string): string => {
      const current = uiTranslations[language];
      if (current && current.genreTypes && current.genreTypes[genreName]) {
        return current.genreTypes[genreName];
      }
      // Fallback to original if translation not found
      return genreName;
    },
    [language, uiTranslations]
  );

  const getPlatformClass = useCallback((platform: string) => {
    const p = platform.toLowerCase();
    if (p.startsWith("ns")) return "platform-ns";
    if (p.startsWith("ps")) return "platform-ps";
    if (p.startsWith("xbox")) return "platform-xbox";
    if (p === "pc") return "platform-pc";
    return "platform-other";
  }, []);

  const itemKey = useCallback((_index: number, group: ReleaseGroup) => group.date, []);

  const normalizeYearPayload = (payload: YearPayload) => {
    if (Array.isArray(payload)) {
      return payload;
    }
    if (payload && Array.isArray(payload.releases)) {
      return payload.releases;
    }
    return [];
  };

  const fetchYear = useCallback(async (year: number) => {
    const response = await fetch(`/data/game-release/${year}.json`);
    if (!response.ok) {
      throw new Error(`Failed to load ${year}.json`);
    }
    const payload: YearPayload = await response.json();
    return sortGroupsByDate(normalizeYearPayload(payload));
  }, []);

  const fetchShowcaseYear = useCallback(async (year: number): Promise<ShowcaseGroup[]> => {
    try {
      const response = await fetch(`/data/showcase/${year}.json`);
      if (!response.ok) {
        return [];
      }
      const data: ShowcaseGroup[] = await response.json();
      return data;
    } catch {
      return [];
    }
  }, []);

  const mergeShowcaseIntoTimeline = useCallback((groups: ReleaseGroup[], showcaseGroups: ShowcaseGroup[]): ReleaseGroup[] => {
    const dateMap = new Map<string, ReleaseGroup>();

    // 先添加游戏数据
    groups.forEach((group) => {
      dateMap.set(group.date, { ...group });
    });

    // 合并 showcase 数据（每个 showcase 自带 displayDate）
    showcaseGroups.forEach((sg) => {
      const existing = dateMap.get(sg.date);
      if (existing) {
        // 合并到已有日期，保留每个 showcase 的 displayDate
        existing.showcases = [...(existing.showcases || []), ...sg.showcases];
      } else {
        // 创建一个新的 group，只有 showcase
        // 使用第一个 showcase 的 displayDate 作为 group 的 displayDate（用于日期显示）
        const groupDisplayDate = sg.showcases[0]?.displayDate || sg.date;
        dateMap.set(sg.date, {
          date: sg.date,
          displayDate: groupDisplayDate,
          games: [],
          showcases: sg.showcases,
        });
      }
    });

    return sortGroupsByDate(Array.from(dateMap.values()));
  }, []);

  // Load game translations
  useEffect(() => {
    const loadTranslations = async () => {
      try {
        const response = await fetch("/data/game-trans.json");
        if (response.ok) {
          const translations: GameTranslation[] = await response.json();
          const translationMap = new Map<string, GameTranslation>();
          translations.forEach((trans) => {
            // 使用英文名作为 key
            translationMap.set(trans.en, trans);
            // 也使用中文名作为 key，以防万一游戏使用中文名
            translationMap.set(trans.zh, trans);
          });
          setGameTranslations(translationMap);
        }
      } catch (err) {
        console.error("Failed to load game translations:", err);
      }
    };
    loadTranslations();
  }, []);

  useEffect(() => {
    let active = true;

    const loadInitial = async () => {
      try {
        const indexResponse = await fetch("/data/game-release/index.json");
        if (!indexResponse.ok) {
          throw new Error("Failed to load release index.");
        }
        const yearFiles: string[] = await indexResponse.json();
        if (!yearFiles.length) {
          throw new Error("Release index is empty.");
        }
        const years = yearFiles
          .map((file) => Number(file.replace(/\.json$/, "")))
          .filter((year) => Number.isFinite(year))
          .sort((a, b) => a - b);
        if (!years.length) {
          throw new Error("Release index is empty.");
        }

        const currentYear = new Date().getFullYear();
        const previousYears = years.filter((year) => year < currentYear);
        const initialYear = years.includes(currentYear)
          ? currentYear
          : previousYears.length
            ? previousYears[previousYears.length - 1]
            : years[0];

        const entries = await fetchYear(initialYear);

        // 加载当年和次年的 showcase 数据
        const showcaseYears = [currentYear, currentYear + 1];
        const showcasePromises = showcaseYears.map((y) => fetchShowcaseYear(y));
        const showcaseResults = await Promise.all(showcasePromises);
        const allShowcases = showcaseResults.flat();

        // 合并 showcase 数据到时间线
        const mergedEntries = mergeShowcaseIntoTimeline(entries, allShowcases);

        if (active) {
          setAvailableYears(years);
          setLoadedYears([initialYear]);
          setTimelineState({
            data: mergedEntries,
            firstItemIndex: INITIAL_FIRST_ITEM_INDEX,
          });
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load timeline.");
        }
      }
    };

    loadInitial();

    return () => {
      active = false;
    };
  }, [fetchYear, fetchShowcaseYear, mergeShowcaseIntoTimeline]);

  const minLoadedYear = loadedYears.length ? Math.min(...loadedYears) : null;
  const maxLoadedYear = loadedYears.length ? Math.max(...loadedYears) : null;

  const prevYear = useMemo(() => {
    if (minLoadedYear === null) {
      return null;
    }
    for (let i = availableYears.length - 1; i >= 0; i -= 1) {
      if (availableYears[i] < minLoadedYear) {
        return availableYears[i];
      }
    }
    return null;
  }, [availableYears, minLoadedYear]);

  const nextYear = useMemo(() => {
    if (maxLoadedYear === null) {
      return null;
    }
    for (let i = 0; i < availableYears.length; i += 1) {
      if (availableYears[i] > maxLoadedYear) {
        return availableYears[i];
      }
    }
    return null;
  }, [availableYears, maxLoadedYear]);

  const loadPrev = useCallback(async () => {
    if (!canAutoLoad || prevYear === null || loadedYears.includes(prevYear) || loadingPrevRef.current) {
      return;
    }
    loadingPrevRef.current = true;
    setLoadingPrev(true);

    // 记住当前可见的第一个项目在数组中的索引
    const currentVisibleArrayIndex = visibleRangeRef.current.startIndex - firstItemIndex;

    try {
      const entries = await fetchYear(prevYear);
      const prevDates = new Set(timelineRef.current.map((group) => group.date));
      const newItems = entries.filter((group) => !prevDates.has(group.date));
      if (newItems.length) {
        // 原子更新 data 和 firstItemIndex
        setTimelineState((prev) => ({
          data: [...newItems, ...prev.data],
          firstItemIndex: prev.firstItemIndex - newItems.length,
        }));

        // 在下一帧滚动到原来可见的位置（新索引 = 原索引 + 新增数量）
        requestAnimationFrame(() => {
          const newArrayIndex = currentVisibleArrayIndex + newItems.length;
          virtuosoRef.current?.scrollToIndex({
            index: newArrayIndex,
            align: "start",
            behavior: "auto",
          });
        });
      }
      setLoadedYears((prev) => (prev.includes(prevYear) ? prev : [...prev, prevYear]));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load timeline.");
    } finally {
      loadingPrevRef.current = false;
      setLoadingPrev(false);
    }
  }, [canAutoLoad, fetchYear, firstItemIndex, loadedYears, prevYear]);

  const loadNext = useCallback(async () => {
    if (!canAutoLoad || nextYear === null || loadedYears.includes(nextYear) || loadingNextRef.current) {
      return;
    }
    loadingNextRef.current = true;
    setLoadingNext(true);

    try {
      const entries = await fetchYear(nextYear);
      const prevDates = new Set(timelineRef.current.map((group) => group.date));
      const newItems = entries.filter((group) => !prevDates.has(group.date));
      if (newItems.length) {
        // append 数据时只需要更新 data，firstItemIndex 保持不变
        setTimelineState((prev) => ({
          ...prev,
          data: [...prev.data, ...newItems],
        }));
      }
      setLoadedYears((prev) => (prev.includes(nextYear) ? prev : [...prev, nextYear]));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load timeline.");
    } finally {
      loadingNextRef.current = false;
      setLoadingNext(false);
    }
  }, [canAutoLoad, fetchYear, loadedYears, nextYear]);

  const markUserInteraction = useCallback(() => {
    setAnimationsEnabled(false);
    setCanAutoLoad(true);
  }, []);

  const findTargetArrayIndexForToday = useCallback(() => {
    if (!timeline.length) {
      return -1;
    }
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayValue = today.getTime();

    let targetIndex = -1;
    let prevIndex = -1;
    let prevValue = 0;
    let nextIndex = -1;
    let nextValue = 0;

    for (let i = 0; i < timeline.length; i += 1) {
      const itemValue = toLocalDayValue(timeline[i].date);
      if (itemValue === null) {
        continue;
      }
      if (itemValue === todayValue) {
        targetIndex = i;
        break;
      }
      if (itemValue < todayValue) {
        prevIndex = i;
        prevValue = itemValue;
        continue;
      }
      if (itemValue > todayValue && nextIndex === -1) {
        nextIndex = i;
        nextValue = itemValue;
      }
    }

    if (targetIndex === -1) {
      if (prevIndex !== -1 && nextIndex !== -1) {
        const prevDiff = todayValue - prevValue;
        const nextDiff = nextValue - todayValue;
        targetIndex = prevDiff <= nextDiff ? prevIndex : nextIndex;
      } else if (prevIndex !== -1) {
        targetIndex = prevIndex;
      } else if (nextIndex !== -1) {
        targetIndex = nextIndex;
      }
    }

    return targetIndex;
  }, [timeline]);

  const scrollToToday = useCallback(
    (smooth = true) => {
      const arrayIndex = findTargetArrayIndexForToday();
      if (arrayIndex < 0) {
        return;
      }
      requestAnimationFrame(() => {
        virtuosoRef.current?.scrollToIndex({
          index: arrayIndex,
          align: "center",
          behavior: smooth ? "smooth" : "auto",
        });
      });
    },
    [findTargetArrayIndexForToday]
  );

  useEffect(() => {
    if (!timeline.length || didInitialScrollRef.current) {
      return;
    }
    didInitialScrollRef.current = true;
    let cancelled = false;
    const targetIndex = findTargetArrayIndexForToday();
    if (targetIndex >= 0) {
      setTimeout(() => {
        if (!cancelled) {
          virtuosoRef.current?.scrollToIndex({
            index: targetIndex,
            align: "center",
            behavior: "auto",
          });
          setCanAutoLoad(true);
        }
      }, 100);
    } else {
      setCanAutoLoad(true);
    }
    return () => {
      cancelled = true;
    };
  }, [findTargetArrayIndexForToday, timeline.length]);

  const onSelectGame = useCallback((game: Game) => {
    setSelectedGame(game);
  }, []);

  const viewDetailsLabel = useMemo(() => t("viewDetails"), [t]);
  const showError = Boolean(error) && !timeline.length;

  // 向上：显示加载中、点击加载上一年、或没有更多数据
  const showTopStatus = Boolean(timeline.length) && canAutoLoad;
  const showBottomStatus = Boolean(timeline.length) && canAutoLoad && (loadingNext || nextYear === null);
  const topStatusText = loadingPrev
    ? t("loadingPrevYear")
    : prevYear !== null
      ? t("clickToLoadPrevYear")
      : t("noMoreData");
  const bottomStatusText = loadingNext ? t("loadingNextYear") : t("noMoreData");
  const canClickLoadPrev = !loadingPrev && prevYear !== null;

  return (
    <>
      <nav className="navbar">
        <div className="nav-content">
          <div className="nav-brand-group">
            <Gamepad2 className="brand-icon" size={24} strokeWidth={1.5} />
            <span className="nav-brand">Wang Qizhi</span>
          </div>
          <div className="nav-controls">
            <button className="theme-toggle" onClick={toggleLanguage} aria-label="Toggle language">
              <Languages size={20} />
              <span className="lang-text">{language === "en" ? "EN" : "中"}</span>
            </button>
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
          <a className="pill" href="https://github.com/wangqizhi">
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
            <h2 className="section-title">{t("timelineTitle")}</h2>
            <p className="section-hint">{t("timelineHint")}</p>
          </div>
          <div className="section-controls">
            <div className="platform-filters">
              {PLATFORM_FILTERS.map((pf) => (
                <button
                  key={pf.key}
                  className={`platform-filter-btn ${pf.className} ${selectedPlatforms.has(pf.key) ? "active" : ""}`}
                  onClick={() => togglePlatform(pf.key)}
                  title={pf.key}
                >
                  {pf.label}
                </button>
              ))}
            </div>
            <button
              className={`showcase-filter-btn ${showOnlyShowcase ? "active" : ""}`}
              onClick={() => setShowOnlyShowcase((prev) => !prev)}
              title="Showcase"
            >
              <Tv size={16} />
              <span>Showcase</span>
            </button>
          </div>
        </div>
        <div
          className="timeline-scroll"
          onWheelCapture={markUserInteraction}
          onTouchStartCapture={markUserInteraction}
          onPointerDownCapture={markUserInteraction}
        >
          <button className="today-btn-floating" onClick={() => scrollToToday(true)} title="Jump to Today">
            <Calendar size={18} />
            <span>{t("today")}</span>
          </button>
          {(loadingPrev || loadingNext) && (
            <div className="timeline-loading-overlay">
              <div className="timeline-loading-spinner" />
              <span>{loadingPrev ? t("loadingPrevYear") : t("loadingNextYear")}</span>
            </div>
          )}
          <div className={`timeline${animationsEnabled ? "" : " no-anim"}`}>
            {showError ? (
              <div className="timeline-item static">
                <div className="timeline-dot" />
                <div className="timeline-date">{t("dataError")}</div>
                <div className="game-card">{error}</div>
              </div>
            ) : timeline.length ? (
              <Virtuoso
                ref={virtuosoRef}
                style={{ height: "100%" }}
                data={timeline}
                firstItemIndex={firstItemIndex}
                increaseViewportBy={1200}
                computeItemKey={itemKey}
                endReached={loadNext}
                rangeChanged={(range) => {
                  visibleRangeRef.current = range;
                }}
                components={{
                  Header: () =>
                    showTopStatus ? (
                      <div className="timeline-status top" aria-live="polite">
                        {canClickLoadPrev ? (
                          <button
                            className="load-prev-btn"
                            onClick={loadPrev}
                            disabled={loadingPrev}
                          >
                            {topStatusText}
                          </button>
                        ) : (
                          <span>{topStatusText}</span>
                        )}
                      </div>
                    ) : null,
                  Footer: () =>
                    showBottomStatus ? (
                      <div className="timeline-status bottom" aria-live="polite">
                        <span>{bottomStatusText}</span>
                      </div>
                    ) : null,
                }}
                itemContent={(virtualIndex: number, group: ReleaseGroup) => {
                  const arrayIndex = virtualIndex - firstItemIndex;
                  const animationDelay = animationsEnabled
                    ? Math.min(Math.max(0, arrayIndex) * ANIMATION_STAGGER_STEP, ANIMATION_MAX_DELAY)
                    : undefined;

                  return (
                    <TimelineGroupItem
                      group={group}
                      selectedPlatforms={selectedPlatforms}
                      matchesPlatformFilter={matchesPlatformFilter}
                      getTranslatedGameName={getTranslatedGameName}
                      getTranslatedGenre={getTranslatedGenre}
                      getPlatformClass={getPlatformClass}
                      viewDetailsLabel={viewDetailsLabel}
                      animationsEnabled={animationsEnabled}
                      animationDelay={animationDelay}
                      onSelectGame={onSelectGame}
                      showOnlyShowcase={showOnlyShowcase}
                      language={language}
                    />
                  );
                }}
              />
            ) : (
              <div className="timeline-item static">
                <div className="timeline-dot" />
                <div className="timeline-date">{t("loading")}</div>
                <div className="game-card">{t("fetchingData")}</div>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
    {selectedGame && (
      <div className="game-modal-overlay" onClick={() => setSelectedGame(null)}>
        <div className="game-modal" onClick={(e) => e.stopPropagation()}>
          <button className="game-modal-close" onClick={() => setSelectedGame(null)}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
          <h3>{getTranslatedGameName(selectedGame.title)}</h3>
          <p className="modal-style">{selectedGame.style}</p>
          <div className="modal-meta">
            <div className="modal-meta-item">
              <span className="modal-meta-label">{t("studio")}</span>
              <span className="modal-meta-value">{selectedGame.studio}</span>
            </div>
            <div className="modal-meta-item">
              <span className="modal-meta-label">{t("platforms")}</span>
              <div className="platform-row">
                {selectedGame.platforms.map((p) => (
                  <span key={p} className={`platform-badge ${getPlatformClass(p)}`}>
                    {p}
                  </span>
                ))}
              </div>
            </div>
            <div className="modal-meta-item">
              <span className="modal-meta-label">{t("genres")}</span>
              <div className="tag-row">
                {selectedGame.genre.map((tag) => (
                  <span key={tag} className="tag">
                    {getTranslatedGenre(tag)}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    )}
    </>
  );
};

export default App;
