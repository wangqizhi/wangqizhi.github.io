import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { flushSync } from "react-dom";
import { Moon, Sun, Gamepad2, Github, Mail, MapPin, Calendar, Languages } from "lucide-react";

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

type ReleaseGroup = {
  date: string;
  displayDate: string;
  games: Game[];
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

const getInitialLanguage = () => {
  if (typeof window === "undefined") {
    return "en" as const;
  }
  const saved = window.localStorage.getItem("language");
  return saved === "zh" || saved === "en" ? saved : "en";
};

const App = () => {
  const [timeline, setTimeline] = useState<ReleaseGroup[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [loadedYears, setLoadedYears] = useState<number[]>([]);
  const [loadingPrev, setLoadingPrev] = useState(false);
  const [loadingNext, setLoadingNext] = useState(false);
  const [canAutoLoad, setCanAutoLoad] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
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
  const scrollRef = useRef<HTMLDivElement>(null);
  const heightsRef = useRef<Map<number, number>>(new Map());
  const didInitialScrollRef = useRef(false);
  const pendingScrollShiftRef = useRef(0);
  const pendingSnapRef = useRef<{
    index: number;
    remaining: number;
    lastMeasureVersion: number;
  } | null>(null);
  const pendingLanguageAnchorRef = useRef<{
    index: number;
    centerDelta: number;
    remaining: number;
    lastMeasureVersion: number;
  } | null>(null);
  const todayJumpRafRef = useRef<number | null>(null);
  const userInteractedRef = useRef(false);
  const lastScrollTopRef = useRef(0);
  const scrollDirectionRef = useRef<"up" | "down" | null>(null);
  const pendingInitialScrollRef = useRef<{
    targetIndex: number;
    yearAnchorIndex: number;
  } | null>(null);
  const scrollRafRef = useRef<number | null>(null);
  const pendingScrollTopRef = useRef<number | null>(null);
  const measureRafRef = useRef<number | null>(null);
  const pendingMeasureVersionRef = useRef(false);
  const [measureVersion, setMeasureVersion] = useState(0);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(0);

  const ESTIMATED_ITEM_HEIGHT = 260;
  const ITEM_GAP = 32;
  const OVERSCAN_PX = 1200;
  const SCROLL_THRESHOLD = 120;
  const SCROLL_SNAP_ATTEMPTS = 3;
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
    if (!timeline.length) {
      setLanguage((prev) => (prev === "en" ? "zh" : "en"));
      return;
    }

    // 语言切换会导致文本换行/高度变化：记录当前“视口中心”锚点，后续在多次 re-measure 后持续校正 scrollTop
    const viewportCenter = scrollTop + viewportHeight / 2;
    const index = findIndexForOffset(viewportCenter);
    const itemTop = offsets[index] ?? 0;
    pendingLanguageAnchorRef.current = {
      index,
      centerDelta: viewportCenter - itemTop,
      remaining: 6,
      lastMeasureVersion: measureVersion,
    };

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

  const getTranslatedGameName = (originalTitle: string): string => {
    const translation = gameTranslations.get(originalTitle);
    if (!translation) return originalTitle;
    return translation[language] || originalTitle;
  };

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

  const getPlatformClass = (platform: string) => {
    const p = platform.toLowerCase();
    if (p.startsWith("ns")) return "platform-ns";
    if (p.startsWith("ps")) return "platform-ps";
    if (p.startsWith("xbox")) return "platform-xbox";
    if (p === "pc") return "platform-pc";
    return "platform-other";
  };

  const normalizeYearPayload = (payload: YearPayload) => {
    if (Array.isArray(payload)) {
      return payload;
    }
    if (payload && Array.isArray(payload.releases)) {
      return payload.releases;
    }
    return [];
  };

  const mergeTimeline = (prev: ReleaseGroup[], entries: ReleaseGroup[]) => {
    const grouped = new Map<string, ReleaseGroup>();
    prev.forEach((entry) => {
      grouped.set(entry.date, {
        date: entry.date,
        displayDate: entry.displayDate,
        games: [...entry.games],
      });
    });
    entries.forEach((entry) => {
      const current = grouped.get(entry.date) ?? {
        date: entry.date,
        displayDate: entry.displayDate || entry.date,
        games: [] as Game[],
      };
      entry.games.forEach((game: Game) => current.games.push(game));
      grouped.set(entry.date, current);
    });
    return Array.from(grouped.values()).sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );
  };

  const resetMeasurements = useCallback(() => {
    heightsRef.current.clear();
    setMeasureVersion((value) => value + 1);
  }, []);

  // 平台筛选改变时重置高度缓存
  useEffect(() => {
    resetMeasurements();
  }, [selectedPlatforms, resetMeasurements]);

  // 语言切换时重置高度缓存（useLayoutEffect 避免中间态闪动）
  useLayoutEffect(() => {
    resetMeasurements();
  }, [language, resetMeasurements]);

  const estimateAddedHeight = useCallback(
    (count: number) => {
      if (count <= 0) {
        return 0;
      }
      return count * (ESTIMATED_ITEM_HEIGHT + ITEM_GAP);
    },
    [ESTIMATED_ITEM_HEIGHT, ITEM_GAP]
  );

  const toLocalDayValue = (dateString: string) => {
    const [year, month, day] = dateString.split("-").map(Number);
    if (!year || !month || !day) {
      return null;
    }
    return new Date(year, month - 1, day).getTime();
  };

  const fetchYear = useCallback(async (year: number) => {
    const response = await fetch(`/data/game-release/${year}.json`);
    if (!response.ok) {
      throw new Error(`Failed to load ${year}.json`);
    }
    const payload: YearPayload = await response.json();
    return normalizeYearPayload(payload);
  }, []);

  const getItemHeight = useCallback(
    (index: number) => heightsRef.current.get(index) ?? ESTIMATED_ITEM_HEIGHT,
    [ESTIMATED_ITEM_HEIGHT]
  );

  const offsets = useMemo(() => {
    const count = timeline.length;
    const result = new Array(count + 1);
    result[0] = 0;
    for (let i = 0; i < count; i += 1) {
      const gap = i === count - 1 ? 0 : ITEM_GAP;
      result[i + 1] = result[i] + getItemHeight(i) + gap;
    }
    return result;
  }, [timeline.length, measureVersion, getItemHeight, ITEM_GAP]);

  const totalHeight = offsets[offsets.length - 1] ?? 0;

  const findIndexForOffset = useCallback(
    (offset: number) => {
      let low = 0;
      let high = offsets.length - 1;
      while (low < high) {
        const mid = Math.floor((low + high) / 2);
        if (offsets[mid] <= offset) {
          low = mid + 1;
        } else {
          high = mid;
        }
      }
      return Math.max(0, low - 1);
    },
    [offsets]
  );

  const visibleRange = useMemo(() => {
    if (!timeline.length) {
      return { start: 0, end: -1 };
    }
    const startOffset = Math.max(0, scrollTop - OVERSCAN_PX);
    const endOffset = scrollTop + viewportHeight + OVERSCAN_PX;
    const start = findIndexForOffset(startOffset);
    const end = Math.min(timeline.length - 1, findIndexForOffset(endOffset));
    return { start, end };
  }, [scrollTop, viewportHeight, timeline.length, findIndexForOffset, OVERSCAN_PX]);

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
        if (active) {
          resetMeasurements();
          setAvailableYears(years);
          setLoadedYears([initialYear]);
          setTimeline(mergeTimeline([], entries));
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
  }, [fetchYear, resetMeasurements]);

  useLayoutEffect(() => {
    const scrollEl = scrollRef.current;
    if (!scrollEl) {
      return;
    }
    const updateViewport = () => {
      setViewportHeight(scrollEl.clientHeight);
    };
    updateViewport();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", updateViewport);
      return () => window.removeEventListener("resize", updateViewport);
    }
    const observer = new ResizeObserver(updateViewport);
    observer.observe(scrollEl);
    return () => observer.disconnect();
  }, []);

  useLayoutEffect(() => {
    if (!pendingScrollShiftRef.current) {
      return;
    }
    const scrollEl = scrollRef.current;
    if (!scrollEl) {
      return;
    }
    const shift = pendingScrollShiftRef.current;
    pendingScrollShiftRef.current = 0;
    const nextScrollTop = scrollEl.scrollTop + shift;
    const maxScrollTop = Math.max(0, totalHeight - scrollEl.clientHeight);
    const clamped = Math.min(Math.max(nextScrollTop, 0), maxScrollTop);
    scrollEl.scrollTop = clamped;
    setScrollTop(clamped);
    // 等待渲染完成后清除过渡状态
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setIsTransitioning(false);
      });
    });
  }, [timeline.length, totalHeight]);

  useEffect(() => {
    const scrollEl = scrollRef.current;
    if (!scrollEl) {
      return;
    }
    const markUserInteraction = () => {
      userInteractedRef.current = true;
      pendingSnapRef.current = null;
      if (todayJumpRafRef.current !== null) {
        window.cancelAnimationFrame(todayJumpRafRef.current);
        todayJumpRafRef.current = null;
      }
      setAnimationsEnabled(false);
      setCanAutoLoad(true);
    };
    const handleWheel = (event: WheelEvent) => {
      markUserInteraction();
      if (event.deltaY > 0) {
        scrollDirectionRef.current = "down";
      } else if (event.deltaY < 0) {
        scrollDirectionRef.current = "up";
      }
    };
    const handleScroll = () => {
      const nextScrollTop = scrollEl.scrollTop;
      if (nextScrollTop !== lastScrollTopRef.current) {
        scrollDirectionRef.current =
          nextScrollTop > lastScrollTopRef.current ? "down" : "up";
        lastScrollTopRef.current = nextScrollTop;
      }
      pendingScrollTopRef.current = nextScrollTop;
      if (scrollRafRef.current !== null) {
        return;
      }
      scrollRafRef.current = window.requestAnimationFrame(() => {
        scrollRafRef.current = null;
        if (pendingScrollTopRef.current !== null) {
          setScrollTop(pendingScrollTopRef.current);
        }
      });
    };
    setScrollTop(scrollEl.scrollTop);
    scrollEl.addEventListener("scroll", handleScroll);
    scrollEl.addEventListener("wheel", handleWheel, { passive: true });
    scrollEl.addEventListener("touchstart", markUserInteraction, { passive: true });
    scrollEl.addEventListener("pointerdown", markUserInteraction);
    return () => {
      scrollEl.removeEventListener("scroll", handleScroll);
      scrollEl.removeEventListener("wheel", handleWheel);
      scrollEl.removeEventListener("touchstart", markUserInteraction);
      scrollEl.removeEventListener("pointerdown", markUserInteraction);
      if (scrollRafRef.current !== null) {
        window.cancelAnimationFrame(scrollRafRef.current);
        scrollRafRef.current = null;
      }
    };
  }, []);

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

  const loadAdjacentYear = useCallback(
    async (year: number, direction: "prev" | "next") => {
      if (loadedYears.includes(year)) {
        return;
      }
      if (direction === "prev") {
        setLoadingPrev(true);
        setIsTransitioning(true);
      } else {
        setLoadingNext(true);
      }
      try {
        const entries = await fetchYear(year);
        if (direction === "prev" && entries.length) {
          // 调整高度缓存索引，而不是清空
          const newHeights = new Map<number, number>();
          heightsRef.current.forEach((height, index) => {
            newHeights.set(index + entries.length, height);
          });
          heightsRef.current = newHeights;
          pendingScrollShiftRef.current += estimateAddedHeight(entries.length);
        } else if (direction === "next") {
          // 追加到末尾时，现有 items 的索引不变：保留高度缓存，避免全量 re-measure 导致卡顿
        }
        setMeasureVersion((v) => v + 1);
        setTimeline((prev) => mergeTimeline(prev, entries));
        setLoadedYears((prev) => (prev.includes(year) ? prev : [...prev, year]));
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load timeline.");
        setIsTransitioning(false);
      } finally {
        if (direction === "prev") {
          setLoadingPrev(false);
        } else {
          setLoadingNext(false);
        }
      }
    },
    [estimateAddedHeight, fetchYear, loadedYears, resetMeasurements]
  );

  useEffect(() => {
    if (!timeline.length || !prevYear || loadingPrev || !canAutoLoad) {
      return;
    }
    if (scrollTop <= SCROLL_THRESHOLD && scrollDirectionRef.current === "up") {
      void loadAdjacentYear(prevYear, "prev");
    }
  }, [
    SCROLL_THRESHOLD,
    canAutoLoad,
    loadAdjacentYear,
    loadingPrev,
    prevYear,
    scrollTop,
    timeline.length,
  ]);

  useEffect(() => {
    if (!timeline.length || !nextYear || loadingNext || !canAutoLoad) {
      return;
    }
    if (
      scrollTop + viewportHeight >= totalHeight - SCROLL_THRESHOLD &&
      scrollDirectionRef.current === "down"
    ) {
      void loadAdjacentYear(nextYear, "next");
    }
  }, [
    SCROLL_THRESHOLD,
    canAutoLoad,
    loadAdjacentYear,
    loadingNext,
    nextYear,
    scrollTop,
    totalHeight,
    viewportHeight,
    timeline.length,
  ]);


  const measureItem = (index: number) => (node: HTMLDivElement | null) => {
    if (!node) {
      return;
    }
    const height = node.getBoundingClientRect().height;
    const prev = heightsRef.current.get(index);
    if (height > 0 && prev !== height) {
      heightsRef.current.set(index, height);
      if (pendingMeasureVersionRef.current) {
        return;
      }
      pendingMeasureVersionRef.current = true;
      if (measureRafRef.current !== null) {
        return;
      }
      measureRafRef.current = window.requestAnimationFrame(() => {
        measureRafRef.current = null;
        pendingMeasureVersionRef.current = false;
        setMeasureVersion((value) => value + 1);
      });
    }
  };

  const findYearAnchorIndex = useCallback(
    (year: number) => {
      const yearPrefix = `${year}-`;
      for (let i = 0; i < timeline.length; i += 1) {
        if (timeline[i].date.startsWith(yearPrefix)) {
          return i;
        }
      }
      return -1;
    },
    [timeline]
  );

  const getScrollTarget = useCallback(
    (index: number) => {
      const scrollEl = scrollRef.current;
      if (!scrollEl) {
        return null;
      }
      const targetTop = offsets[index] ?? 0;
      const targetHeight = getItemHeight(index);
      const offset = targetTop - scrollEl.clientHeight / 2 + targetHeight / 2;
      const maxScrollTop = Math.max(0, totalHeight - scrollEl.clientHeight);
      const clamped = Math.min(Math.max(offset, 0), maxScrollTop);
      return { clamped, scrollEl };
    },
    [getItemHeight, offsets, totalHeight]
  );

  const scrollToIndex = useCallback(
    (index: number, smooth: boolean) => {
      const target = getScrollTarget(index);
      if (!target) {
        return;
      }
      if (smooth) {
        target.scrollEl.scrollTo({ top: target.clamped, behavior: "smooth" });
      } else {
        // 使用 flushSync 强制同步更新状态，确保 visibleRange 立即基于新的 scrollTop 计算
        target.scrollEl.scrollTop = target.clamped;
        flushSync(() => {
          setScrollTop(target.scrollEl.scrollTop);
        });
      }
    },
    [getScrollTarget]
  );

  const scrollToToday = useCallback(
    (smooth = true) => {
      if (!timeline.length) {
        return;
      }
      if (todayJumpRafRef.current !== null) {
        window.cancelAnimationFrame(todayJumpRafRef.current);
        todayJumpRafRef.current = null;
      }

      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const todayValue = today.getTime();
      const yearAnchorIndex = findYearAnchorIndex(today.getFullYear());

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
        if (itemValue > todayValue) {
          nextIndex = i;
          nextValue = itemValue;
          break;
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

      if (targetIndex === -1) {
        return;
      }

      const runSecondStep = () => {
        scrollToIndex(targetIndex, smooth);
        pendingSnapRef.current = {
          index: targetIndex,
          remaining: SCROLL_SNAP_ATTEMPTS,
          lastMeasureVersion: measureVersion,
        };
      };

      if (yearAnchorIndex !== -1) {
        scrollToIndex(yearAnchorIndex, false);
        todayJumpRafRef.current = window.requestAnimationFrame(() => {
          todayJumpRafRef.current = window.requestAnimationFrame(() => {
            todayJumpRafRef.current = null;
            runSecondStep();
          });
        });
      } else {
        runSecondStep();
      }
    },
    [findYearAnchorIndex, measureVersion, scrollToIndex, timeline]
  );

  useEffect(() => {
    const pending = pendingSnapRef.current;
    if (!pending) {
      return;
    }
    if (!timeline.length) {
      pendingSnapRef.current = null;
      return;
    }
    const target = getScrollTarget(pending.index);
    if (!target) {
      pendingSnapRef.current = null;
      return;
    }
    const delta = Math.abs(scrollTop - target.clamped);
    if (delta <= 2) {
      pendingSnapRef.current = null;
      return;
    }
    if (pending.remaining <= 0) {
      pendingSnapRef.current = null;
      return;
    }
    if (measureVersion === pending.lastMeasureVersion) {
      return;
    }
    pending.lastMeasureVersion = measureVersion;
    pending.remaining -= 1;
    target.scrollEl.scrollTop = target.clamped;
    flushSync(() => {
      setScrollTop(target.scrollEl.scrollTop);
    });
  }, [getScrollTarget, measureVersion, scrollTop, timeline.length]);

  useLayoutEffect(() => {
    const pending = pendingLanguageAnchorRef.current;
    const scrollEl = scrollRef.current;
    if (!pending || !scrollEl) {
      return;
    }
    if (!timeline.length) {
      pendingLanguageAnchorRef.current = null;
      return;
    }
    if (pending.remaining <= 0) {
      pendingLanguageAnchorRef.current = null;
      return;
    }
    if (measureVersion === pending.lastMeasureVersion) {
      return;
    }
    pending.lastMeasureVersion = measureVersion;
    pending.remaining -= 1;

    const nextItemTop = offsets[pending.index] ?? 0;
    const targetScrollTop = nextItemTop + pending.centerDelta - viewportHeight / 2;
    const maxScrollTop = Math.max(0, totalHeight - scrollEl.clientHeight);
    const clamped = Math.min(Math.max(targetScrollTop, 0), maxScrollTop);
    scrollEl.scrollTop = clamped;
    flushSync(() => {
      setScrollTop(clamped);
    });
  }, [measureVersion, offsets, timeline.length, totalHeight, viewportHeight]);

  // 第一步：在timeline首次加载时计算目标索引
  useEffect(() => {
    if (!timeline.length || didInitialScrollRef.current) {
      return;
    }
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayValue = today.getTime();
    const yearAnchorIndex = findYearAnchorIndex(today.getFullYear());

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
      if (itemValue > todayValue) {
        nextIndex = i;
        nextValue = itemValue;
        break;
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

    if (targetIndex !== -1) {
      pendingInitialScrollRef.current = {
        targetIndex,
        yearAnchorIndex,
      };
    }
  }, [timeline.length, findYearAnchorIndex, toLocalDayValue]);

  // 第二步：在offsets计算完成后执行初始滚动
  useEffect(() => {
    if (!pendingInitialScrollRef.current || didInitialScrollRef.current) {
      return;
    }

    const pending = pendingInitialScrollRef.current;
    pendingInitialScrollRef.current = null;

    let cancelled = false;
    const rafId = window.requestAnimationFrame(() => {
      if (cancelled) {
        return;
      }
      
      const runSecondStep = () => {
        scrollToIndex(pending.targetIndex, false);
        pendingSnapRef.current = {
          index: pending.targetIndex,
          remaining: SCROLL_SNAP_ATTEMPTS,
          lastMeasureVersion: measureVersion,
        };
      };

      if (pending.yearAnchorIndex !== -1) {
        scrollToIndex(pending.yearAnchorIndex, false);
        window.requestAnimationFrame(() => {
          window.requestAnimationFrame(() => {
            if (!cancelled) {
              runSecondStep();
              didInitialScrollRef.current = true;
            }
          });
        });
      } else {
        runSecondStep();
        didInitialScrollRef.current = true;
      }
    });
    
    return () => {
      cancelled = true;
      window.cancelAnimationFrame(rafId);
    };
  }, [scrollToIndex, measureVersion]);

  const visibleGroups =
    visibleRange.end >= visibleRange.start
      ? timeline.slice(visibleRange.start, visibleRange.end + 1)
      : [];

  const filterGames = useCallback(
    (games: Game[]) => {
      if (selectedPlatforms.size === 0) {
        return games;
      }
      return games.filter((game) => matchesPlatformFilter(game.platforms));
    },
    [selectedPlatforms, matchesPlatformFilter]
  );
  const topSpacer = timeline.length ? offsets[visibleRange.start] ?? 0 : 0;
  const endOffset =
    visibleRange.end >= 0 ? offsets[visibleRange.end + 1] ?? topSpacer : topSpacer;
  const bottomSpacer = timeline.length
    ? Math.max(0, totalHeight - endOffset)
    : 0;
  const timelineStyle = timeline.length
    ? { paddingTop: topSpacer, paddingBottom: bottomSpacer }
    : undefined;
  const showError = Boolean(error) && !timeline.length;
  const hasPrev = prevYear !== null;
  const hasNext = nextYear !== null;
  const isNearTop = scrollTop <= SCROLL_THRESHOLD;
  const isNearBottom = scrollTop + viewportHeight >= totalHeight - SCROLL_THRESHOLD;
  const isScrollingUp = scrollDirectionRef.current === "up";
  const isScrollingDown = scrollDirectionRef.current === "down";
  const showTopStatus =
    Boolean(timeline.length) &&
    canAutoLoad &&
    isNearTop &&
    (loadingPrev || (!hasPrev && isScrollingUp));
  const showBottomStatus =
    Boolean(timeline.length) &&
    canAutoLoad &&
    isNearBottom &&
    (loadingNext || (!hasNext && isScrollingDown));
  const topStatusText = loadingPrev ? t("loadingPrevYear") : t("noMoreData");
  const bottomStatusText = loadingNext ? t("loadingNextYear") : t("noMoreData");

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
            <button className="today-btn" onClick={() => scrollToToday(true)} title="Jump to Today">
              <Calendar size={18} />
              <span>{t("today")}</span>
            </button>
          </div>
        </div>
        <div className="timeline-scroll" ref={scrollRef}>
          {isTransitioning && (
            <div className="timeline-loading-overlay">
              <div className="timeline-loading-spinner" />
              <span>{t("loading")}</span>
            </div>
          )}
          {showTopStatus ? (
            <div className="timeline-status top" aria-live="polite">
              <span>{topStatusText}</span>
            </div>
          ) : null}
          <div
            className={`timeline${animationsEnabled ? "" : " no-anim"}`}
            style={timelineStyle}
          >
            {showError ? (
              <div className="timeline-item static">
                <div className="timeline-dot" />
                <div className="timeline-date">{t("dataError")}</div>
                <div className="game-card">{error}</div>
              </div>
            ) : timeline.length ? (
              visibleGroups.map((group, index) => {
                const absoluteIndex = visibleRange.start + index;
                const animationDelay = Math.min(
                  index * ANIMATION_STAGGER_STEP,
                  ANIMATION_MAX_DELAY
                );
                const filteredGames = filterGames(group.games);
                if (filteredGames.length === 0) {
                  // 渲染隐藏占位符以保持虚拟滚动索引正确
                  return (
                    <div
                      key={group.date}
                      className="timeline-item-placeholder"
                      ref={measureItem(absoluteIndex)}
                      aria-hidden="true"
                    />
                  );
                }
                return (
                  <div
                    key={group.date}
                    className="timeline-item"
                    style={{
                      animationDelay: `${animationDelay}s`,
                    }}
                    data-date={group.date}
                    ref={measureItem(absoluteIndex)}
                  >
                    <div className="timeline-dot" />
                    <div className="timeline-date">{group.displayDate}</div>
                    <div className="game-card-wrapper">
                      {filteredGames.map((game) => (
                        <div key={game.title} className="game-card">
                          <div className="game-card-header">
                            <h3>{getTranslatedGameName(game.title)}</h3>
                            <button 
                              className="game-detail-btn"
                              onClick={() => setSelectedGame(game)}
                              aria-label={t("viewDetails")}
                            >
                              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="1"/>
                                <circle cx="19" cy="12" r="1"/>
                                <circle cx="5" cy="12" r="1"/>
                              </svg>
                            </button>
                          </div>
                          <p className="game-style" title={game.style}>{game.style}</p>
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
              })
            ) : (
              <div className="timeline-item static">
                <div className="timeline-dot" />
                <div className="timeline-date">{t("loading")}</div>
                <div className="game-card">{t("fetchingData")}</div>
              </div>
            )}
          </div>
          {showBottomStatus ? (
            <div className="timeline-status bottom" aria-live="polite">
              <span>{bottomStatusText}</span>
            </div>
          ) : null}
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
