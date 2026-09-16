import { StrictMode, useEffect, useMemo, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import { ArrowRight, ChevronLeft, ChevronRight, Filter, LogIn, Plus, Search, X } from "lucide-react";
import "./styles.css";

type Listing = {
  id: number;
  major: "mat" | "iisi" | "iad" | "mad" | "cs";
  semester: number;
  subject: string;
  classType: "tutorial" | "labs" | "project";
  groupHave: string;
  groupWant: string[];
  description: string;
  createdAt: string;
  status: "active" | "pending" | "fulfilled" | "stale" | "cancelled";
};

type ExchangeRequest = {
  id: number;
  listing_id: number;
  requester_id: number;
  status: "pending" | "confirmed" | "expired" | "cancelled";
  created_at: string;
  expires_at: string;
  confirmed_at: string | null;
  requester_email?: string | null;
  owner_email?: string | null;
  is_owner: boolean;
  listing: Listing | null;
};

type Filters = {
  major: string[];
  subject: string;
  semester: string;
  classType: string;
  groupHave: string;
  groupWant: string;
};

const defaultFilters: Filters = { major: [], subject: "", semester: "", classType: "", groupHave: "", groupWant: "" };

const majorLabels = {
  pl: { mat: "Mat", iisi: "IiSI", iad: "IiAD", mad: "MAD", cs: "CS" },
  en: { mat: "Mat", iisi: "IiSI", iad: "IiAD", mad: "MAD", cs: "CS" },
} as const;

const classTypeLabels = {
  pl: { tutorial: "Ćwiczenia", labs: "Laby", project: "Projekt" },
  en: { tutorial: "tutorial", labs: "labs", project: "project" },
} as const;

function formatApiError(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object" && "msg" in item) return String(item.msg);
      return JSON.stringify(item);
    }).join("; ");
  }
  if (detail && typeof detail === "object" && "message" in detail) return String(detail.message);
  return fallback;
}

function parseGroups(value: string): string[] {
  return [...new Set(value.split(",").map((group) => group.trim()).filter(Boolean))]
    .sort((left, right) => Number(left) - Number(right));
}
function areNumericGroups(groups: string[]): boolean {
  return groups.length > 0 && groups.every((group) => /^\d+$/.test(group));
}

function mapListing(listing: Record<string, unknown>): Listing {
  return {
    id: Number(listing.id),
    major: listing.major as Listing["major"],
    semester: Number(listing.semester),
    subject: String(listing.subject),
    classType: listing.class_type as Listing["classType"],
    groupHave: String(listing.group_have ?? "?"),
    groupWant: Array.isArray(listing.group_want) ? listing.group_want.map(String) : [],
    description: String(listing.description ?? ""),
    createdAt: String(listing.created_at),
    status: listing.status as Listing["status"],
  };
}

function daysAgoLabel(createdAt: string, language: "pl" | "en"): string {
  const days = Math.max(0, Math.floor((Date.now() - new Date(createdAt).getTime()) / 86_400_000));
  if (language === "en") return days === 0 ? "today" : `${days} days ago`;
  if (days === 0) return "dzisiaj";
  if (days === 1) return "wczoraj";
  return `${days} dni temu`;
}

function App() {
  const [language, setLanguage] = useState<"pl" | "en">("pl");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [accessToken, setAccessToken] = useState("");
  const [authMode, setAuthMode] = useState<"login" | "register" | "reset-request" | "reset-confirm" | "resend-verification" | null>(null);
  const [authForm, setAuthForm] = useState({ email: "", indexNumber: "", password: "" });
  const [resetToken, setResetToken] = useState("");
  const [authError, setAuthError] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [exchangeOpen, setExchangeOpen] = useState(false);
  const [exchangeRequests, setExchangeRequests] = useState<ExchangeRequest[]>([]);
  const [exchangeBusy, setExchangeBusy] = useState(false);
  const [myListings, setMyListings] = useState<Listing[]>([]);
  const [toast, setToast] = useState("");
  const [listings, setListings] = useState<Listing[]>([]);
  const [listingsLoading, setListingsLoading] = useState(true);
  const [listingsError, setListingsError] = useState("");
  const [fulfilledExchanges, setFulfilledExchanges] = useState<number | null>(null);
  const [filterOpen, setFilterOpen] = useState(false);
  const [filters, setFilters] = useState(defaultFilters);
  const [draftFilters, setDraftFilters] = useState(defaultFilters);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [step, setStep] = useState(1);
  const [newListing, setNewListing] = useState({
    major: "mat" as Listing["major"],
    semester: "3",
    subject: "",
    classType: "tutorial" as Listing["classType"],
    groupHave: "",
    groupWant: "",
  });
  const [groupHaveDraft, setGroupHaveDraft] = useState("");
  const [groupWantDraft, setGroupWantDraft] = useState("");
  const maintenanceMode = import.meta.env.VITE_MAINTENANCE === "true";

  useEffect(() => {
    const savedToken = window.localStorage.getItem("spindel_access_token");
    const urlToken = new URLSearchParams(window.location.search).get("token");
    if (savedToken) {
      setAccessToken(savedToken);
      setIsLoggedIn(true);
    }
    if (urlToken && window.location.pathname === "/reset-password") {
      setResetToken(urlToken);
      setAuthMode("reset-confirm");
      window.history.replaceState({}, "", "/reset-password");
    }
    if (urlToken && window.location.pathname === "/verify") {
      window.history.replaceState({}, "", "/verify");
      fetch(`/api/verify?token=${encodeURIComponent(urlToken)}`)
        .then(async (response) => {
          if (!response.ok) {
            const data = await response.json().catch(() => null);
            throw new Error(formatApiError(data?.detail, "Nie udało się potwierdzić emaila."));
          }
          setToast(copy.activatedHelp);
          setAuthMode("login");
        })
        .catch((error) => setToast(error instanceof Error ? error.message : "Nie udało się potwierdzić emaila."));
    }
  }, []);

  const reloadListings = async () => {
    const response = await fetch("/api/listings");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json() as Array<Record<string, unknown>>;
    setListings(data.map(mapListing));
  };

  useEffect(() => {
    let cancelled = false;
    reloadListings()
      .then(() => {
        if (cancelled) return;
        setListingsError("");
      })
      .catch(() => {
          if (!cancelled) setListingsError(language === "pl" ? "Nie udało się pobrać ogłoszeń z backendu." : "Could not load listings from the backend.");
      })
      .finally(() => {
        if (!cancelled) setListingsLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    fetch("/api/stats")
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((data: { fulfilled_exchanges: number }) => setFulfilledExchanges(data.fulfilled_exchanges))
      .catch(() => setFulfilledExchanges(null));
  }, []);

  const filteredListings = useMemo(() => {
    return listings.filter((listing) => {
      const majorMatch = filters.major.length === 0 || filters.major.includes(listing.major);
      const subjectMatch = !filters.subject || listing.subject === filters.subject;
      const semesterMatch = !filters.semester || listing.semester === Number(filters.semester);
      const classTypeMatch = !filters.classType || listing.classType === filters.classType;
      const groupHaveMatch = !filters.groupHave || listing.groupHave === filters.groupHave;
      const wantedGroups = parseGroups(filters.groupWant);
      const groupWantMatch = wantedGroups.length === 0 || wantedGroups.some((group) => listing.groupWant.includes(group));
      return majorMatch && subjectMatch && semesterMatch && classTypeMatch && groupHaveMatch && groupWantMatch;
    });
  }, [filters, listings]);

  const activeFilterCount = filters.major.length + [filters.subject, filters.semester, filters.classType, filters.groupHave, filters.groupWant].filter(Boolean).length;
  const subjectOptions = [...new Set(listings.filter((listing) => draftFilters.major.length === 0 || draftFilters.major.includes(listing.major)).map((listing) => listing.subject))].sort();
  const wantedGroups = parseGroups(newListing.groupWant);
  const groupFormValid = /^\d+$/.test(newListing.groupHave.trim()) && areNumericGroups(wantedGroups) && !wantedGroups.includes(newListing.groupHave.trim());
  const copy = language === "pl" ? {
    login: "Zaloguj", register: "Załóż konto", logout: "Wyloguj", add: "Dodaj ogłoszenie",
    eyebrow: "Wymiana grup zajęciowych PW MiNI", title: "Znajdź lepszą grupę.",
    intro: "Przejrzyście, bez chaosu. Wybierz zajęcia, grupę i kierunek zamiany.",
    active: "Aktywne ogłoszenia", filters: "Filtry", haveWant: "mam → szukam",
    fulfilled: "Pomyślnie zrealizowanych zamian",
    interested: "Zainteresuj się wymianą", back: "Wstecz", next: "Dalej", publish: "Opublikuj",
    loading: "Ładowanie ogłoszeń...", emptyTitle: "Nic tu jeszcze nie ma", emptyText: "Spróbuj zmienić filtry albo dodaj własne ogłoszenie.",
    maintenanceTitle: "Krótka przerwa techniczna", maintenanceText: "Pracujemy nad aplikacją. Wrócimy za chwilę.", footer: "Wymiana grup dla studentów PW",
    anySubject: "Każdy przedmiot", anySemester: "Każdy semestr", anyType: "Każdy typ", clear: "Wyczyść", showResults: "Pokaż wyniki",
    narrow: "Zawęź listę", filterTitle: "Filtry", direction: "Kierunek", subject: "Przedmiot", semester: "Semestr", classType: "Typ zajęć", haveGroup: "Mam grupę", wantGroup: "Szukam grupy", close: "Zamknij", newListing: "Nowe ogłoszenie", cancel: "Anuluj", sent: "Wysłane", received: "Otrzymane", completed: "Zakończone", myListings: "Moje ogłoszenia", noSent: "Brak wysłanych zgłoszeń.", noReceived: "Brak otrzymanych zgłoszeń.", noCompleted: "Brak zakończonych wymian.", noListings: "Brak własnych ogłoszeń.", confirm: "Potwierdź", reject: "Odrzuć", contact: "Kontakt",
    loginTitle: "Zaloguj się", registerTitle: "Załóż konto", resetTitle: "Reset hasła", resetConfirmTitle: "Ustaw nowe hasło", resendTitle: "Wyślij ponownie link", email: "Email", password: "Hasło", newPassword: "Nowe hasło", indexNumber: "Numer indeksu", send: "Wyślij", changePassword: "Zmień hasło", wait: "Chwila...",
    subjectPlaceholder: "np. Algebra", groupPlaceholder: "np. 12", wantedPlaceholder: "np. 14, 15, 16", backLabel: "Wstecz", nextLabel: "Dalej", publishLabel: "Opublikuj", cancelLabel: "Anuluj", forgotPassword: "Nie pamiętam hasła", resendLink: "Wyślij ponownie link weryfikacyjny", resetHelp: "Link resetu jest ważny przez godzinę.", emailHelp: "Podaj email użyty przy rejestracji.", activatedHelp: "Email potwierdzony. Zaloguj się na stronie Spindel.",
  } : {
    login: "Log in", register: "Create account", logout: "Log out", add: "Add listing",
    eyebrow: "PW MiNI group exchange", title: "Find a better group.",
    intro: "Clear and calm. Choose a class, group and exchange direction.",
    active: "Active listings", filters: "Filters", haveWant: "have → want",
    fulfilled: "Successfully completed exchanges",
    interested: "Interested in this exchange", back: "Back", next: "Next", publish: "Publish",
    loading: "Loading listings...", emptyTitle: "Nothing here yet", emptyText: "Try changing filters or add your own listing.",
    maintenanceTitle: "Short maintenance break", maintenanceText: "We are working on the app. We will be back shortly.", footer: "Group exchange for PW students",
    anySubject: "Any subject", anySemester: "Any semester", anyType: "Any class type", clear: "Clear", showResults: "Show results",
    narrow: "Narrow the list", filterTitle: "Filters", direction: "Major", subject: "Subject", semester: "Semester", classType: "Class type", haveGroup: "Have group", wantGroup: "Want group", close: "Close", newListing: "New listing", cancel: "Cancel", sent: "Sent", received: "Received", completed: "Completed", myListings: "My listings", noSent: "No sent requests.", noReceived: "No received requests.", noCompleted: "No completed exchanges.", noListings: "No own listings.", confirm: "Confirm", reject: "Reject", contact: "Contact",
    loginTitle: "Log in", registerTitle: "Create account", resetTitle: "Password reset", resetConfirmTitle: "Set a new password", resendTitle: "Resend verification link", email: "Email", password: "Password", newPassword: "New password", indexNumber: "Index number", send: "Send", changePassword: "Change password", wait: "Please wait...",
    subjectPlaceholder: "e.g. Algebra", groupPlaceholder: "e.g. 12", wantedPlaceholder: "e.g. 14, 15, 16", backLabel: "Back", nextLabel: "Next", publishLabel: "Publish", cancelLabel: "Cancel", forgotPassword: "I forgot my password", resendLink: "Resend verification link", resetHelp: "The reset link is valid for one hour.", emailHelp: "Enter the email used during registration.", activatedHelp: "Email confirmed. Log in on the Spindel website.",
  };

  const applyFilters = () => {
    setFilters(draftFilters);
    setFilterOpen(false);
  };

  const openAuth = (mode: "login" | "register") => {
    setAuthMode(mode);
    setAuthError("");
    setAuthForm({ email: "", indexNumber: "", password: "" });
  };

  const openUtilityAuth = (mode: "reset-request" | "resend-verification") => {
    setAuthMode(mode);
    setAuthError("");
    setAuthForm({ email: "", indexNumber: "", password: "" });
  };

  const submitAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    const endpoint = authMode === "login" ? "/api/login" : "/api/register";
    const body = authMode === "login"
      ? { email: authForm.email, password: authForm.password }
      : { email: authForm.email, index_number: authForm.indexNumber, password: authForm.password };
    try {
      const response = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data = await response.json();
      if (!response.ok) throw new Error(formatApiError(data.detail, "Nie udało się wykonać operacji."));
      if (authMode === "login") {
        setAccessToken(data.access_token);
        setIsLoggedIn(true);
        window.localStorage.setItem("spindel_access_token", data.access_token);
        setAuthMode(null);
      } else {
        setAuthMode(null);
        setToast(language === "pl" ? "Jeśli dane są poprawne, sprawdź email i kliknij link aktywacyjny." : "If the data is valid, check your email and click the activation link.");
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Nie udało się wykonać operacji.");
    } finally {
      setAuthBusy(false);
    }
  };

  const submitUtilityAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    const isResetRequest = authMode === "reset-request";
    const endpoint = isResetRequest ? "/api/password-reset/request" : "/api/resend-verification";
    try {
      const response = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: authForm.email }) });
      const data = response.status === 204 ? null : await response.json();
      if (!response.ok) throw new Error(formatApiError(data?.detail, "Nie udało się wykonać operacji."));
      setAuthMode(null);
      setToast(isResetRequest ? (language === "pl" ? "Jeśli konto istnieje, wysłaliśmy wiadomość z linkiem." : "If the account exists, we sent a message with a link.") : (language === "pl" ? "Jeśli można wysłać wiadomość, otrzymasz nowy link weryfikacyjny." : "If we can send a message, you will receive a new verification link."));
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Nie udało się wykonać operacji.");
    } finally {
      setAuthBusy(false);
    }
  };

  const submitPasswordReset = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    try {
      const response = await fetch("/api/password-reset/confirm", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token: resetToken, password: authForm.password }) });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(formatApiError(data.detail, "Link resetu jest nieprawidłowy lub wygasł."));
      }
      setAuthMode("login");
      setAuthForm({ email: "", indexNumber: "", password: "" });
      setToast(language === "pl" ? "Hasło zmienione. Możesz się teraz zalogować." : "Password changed. You can now log in.");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : (language === "pl" ? "Nie udało się zmienić hasła." : "Could not change the password."));
    } finally {
      setAuthBusy(false);
    }
  };

  const requestExchange = async (listingId: number) => {
    if (!isLoggedIn || !accessToken) {
      setToast(language === "pl" ? "Zaloguj się lub załóż konto, aby wysłać zgłoszenie." : "Log in or create an account to send a request.");
      return;
    }
    try {
      const response = await fetch(`/api/listings/${listingId}/requests`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(formatApiError(data.detail, "Nie udało się wysłać zgłoszenia."));
      setSelectedListing(null);
      setToast(language === "pl" ? "Zgłoszenie wysłane." : "Request sent.");
      await reloadListings();
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Nie udało się wysłać zgłoszenia.");
    }
  };

  const loadExchangeRequests = async () => {
    try {
      const response = await fetch("/api/me/exchange-requests", { headers: { Authorization: `Bearer ${accessToken}` } });
      const data = await response.json();
      if (response.status === 401) {
        setIsLoggedIn(false);
        setAccessToken("");
        window.localStorage.removeItem("spindel_access_token");
      }
      if (!response.ok) throw new Error(formatApiError(data.detail, "Nie udało się pobrać wymian."));
      setExchangeRequests(data.map((request: ExchangeRequest & { listing?: Record<string, unknown> | null }) => ({
        ...request,
        listing: request.listing ? mapListing(request.listing) : null,
      })));
      try {
        await loadMyListings();
      } catch {
        setMyListings([]);
      }
      setExchangeOpen(true);
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Nie udało się pobrać wymian.");
    }
  };

  const loadMyListings = async () => {
    const response = await fetch("/api/me/listings", { headers: { Authorization: `Bearer ${accessToken}` } });
    if (!response.ok) throw new Error(language === "pl" ? "Nie udało się pobrać własnych ogłoszeń." : "Could not load your listings.");
    const data = await response.json() as Array<Record<string, unknown>>;
    setMyListings(data.map(mapListing));
  };

  const exchangeAction = async (requestId: number, action: "confirm" | "reject") => {
    const question = action === "confirm"
      ? "Potwierdzić wymianę? Ogłoszenie zostanie zamknięte, a emaile obu osób zostaną ujawnione."
      : "Odrzucić zgłoszenie i anulować to ogłoszenie? Tej operacji nie można cofnąć.";
    if (!window.confirm(question)) return;
    setExchangeBusy(true);
    try {
      const response = await fetch(`/api/exchange-requests/${requestId}/${action}`, { method: "POST", headers: { Authorization: `Bearer ${accessToken}` } });
      const data = await response.json();
      if (!response.ok) throw new Error(formatApiError(data.detail, "Operacja nie powiodła się."));
      setToast(action === "confirm" ? "Wymiana potwierdzona." : "Ogłoszenie anulowane.");
      await loadExchangeRequests();
      await loadMyListings();
      await reloadListings();
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Operacja nie powiodła się.");
    } finally {
      setExchangeBusy(false);
    }
  };

  const cancelListing = async (listingId: number) => {
    if (!window.confirm("Anulować to ogłoszenie? Nie będzie już widoczne na liście.")) return;
    setExchangeBusy(true);
    try {
      const response = await fetch(`/api/listings/${listingId}/cancel`, { method: "POST", headers: { Authorization: `Bearer ${accessToken}` } });
      const data = await response.json();
      if (!response.ok) throw new Error(formatApiError(data.detail, "Nie udało się anulować ogłoszenia."));
      setToast("Ogłoszenie anulowane.");
      await loadExchangeRequests();
      await loadMyListings();
      await reloadListings();
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Nie udało się anulować ogłoszenia.");
    } finally {
      setExchangeBusy(false);
    }
  };

  const completedRequests = exchangeRequests.filter((request) => request.status === "confirmed");
  const openRequests = exchangeRequests.filter((request) => request.status !== "confirmed");
  const sentRequests = openRequests.filter((request) => !request.is_owner);
  const receivedRequests = openRequests.filter((request) => request.is_owner);
  const requestTitle = (request: ExchangeRequest) => {
    const listing = request.listing;
    if (!listing) return `Ogłoszenie #${request.listing_id}`;
    const wantedGroups = Array.isArray(listing.groupWant) ? listing.groupWant.join(", ") : "?";
    return `${listing.subject} · gr. ${listing.groupHave} → ${wantedGroups}`;
  };

  if (maintenanceMode) {
    return <main className="maintenance-screen"><div className="maintenance-mark">S</div><p className="eyebrow">Spindel</p><h1>{copy.maintenanceTitle}</h1><p>{copy.maintenanceText}</p></main>;
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={() => setFilters(defaultFilters)} aria-label="Wróć do listy ogłoszeń">
          <span className="brand-mark">S</span>
          <span>Spindel</span>
        </button>
        <nav className="account-actions" aria-label="Konto">
          <button className="language-button" onClick={() => setLanguage(language === "pl" ? "en" : "pl")} aria-label="Zmień język">
            {language.toUpperCase()} / {language === "pl" ? "EN" : "PL"}
          </button>
          {isLoggedIn ? (
            <>
              <button className="text-button" onClick={() => { setIsLoggedIn(false); setAccessToken(""); window.localStorage.removeItem("spindel_access_token"); }}>{copy.logout}</button>
                          <button className="outline-button compact" onClick={loadExchangeRequests}>Moje wymiany</button>
              <button className="primary-button compact" onClick={() => { setStep(1); setAddOpen(true); }}>
                <Plus size={17} /> {copy.add}
              </button>
            </>
          ) : (
            <>
              <button className="text-button" onClick={() => openAuth("login")}><LogIn size={17} /> {copy.login}</button>
              <button className="outline-button compact" onClick={() => openAuth("register")}>{copy.register}</button>
            </>
          )}
        </nav>
      </header>

      <section className="hero-row">
        <div>
          <p className="eyebrow">{copy.eyebrow}</p>
          <h1>{copy.title}</h1>
          <p className="hero-copy">{copy.intro}</p>
        </div>
        <aside className="blueprint" aria-label="Budowa karty ogłoszenia">
          <p className="blueprint-title">Blueprint</p>
          <div className="blueprint-row"><span className="blueprint-chip teal">kierunek</span><span className="blueprint-chip yellow">typ zajęć</span></div>
          <strong>semestr: przedmiot</strong>
          <div className="blueprint-exchange"><span className="blueprint-chip blue">mam</span><ArrowRight size={15} /><span className="blueprint-chip teal">szukam</span></div>
        </aside>
      </section>

      {fulfilledExchanges !== null && <div className="trust-line"><strong>{fulfilledExchanges}</strong> {copy.fulfilled}</div>}

      <section className="list-toolbar" aria-label="Narzędzia listy">
        <div className="result-count">{listingsLoading ? copy.loading : copy.active} {!listingsLoading && <strong>{filteredListings.length}</strong>}</div>
        <button className="filter-button" onClick={() => { setDraftFilters(filters); setFilterOpen(true); }}>
          <Filter size={18} /> {copy.filters} {activeFilterCount > 0 && <span className="filter-count">{activeFilterCount}</span>}
        </button>
      </section>

      {listingsError && <div className="empty-state compact-state"><p>{listingsError}</p></div>}

      <section className="listing-grid" aria-label="Lista ogłoszeń">
        {filteredListings.map((listing) => (
          <article className="listing-card" key={listing.id} onClick={() => setSelectedListing(listing)}>
            <div className="card-tags">
              <span className="tag tag-major">{majorLabels[language][listing.major]}</span>
              <span className="tag tag-type">{classTypeLabels[language][listing.classType]}</span>
            </div>
            <h2><span>{listing.semester}:</span> {listing.subject}</h2>
            <div className="exchange-label">{copy.haveWant}</div>
            <div className="exchange-line">
              <span className="group-pill have">{listing.groupHave}</span>
              <ArrowRight className="exchange-arrow" size={22} />
              <div className="wanted-groups">
                {listing.groupWant.map((group) => <span className="group-pill want" key={group}>{group}</span>)}
              </div>
            </div>
            <p>{listing.description}</p>
            <div className="card-footer"><span>{daysAgoLabel(listing.createdAt, language)}</span><ChevronRight size={18} /></div>
          </article>
        ))}
      </section>

      {filteredListings.length === 0 && <div className="empty-state"><Search size={28} /><h2>{copy.emptyTitle}</h2><p>{copy.emptyText}</p></div>}

      {filterOpen && <div className="modal-backdrop" onMouseDown={() => setFilterOpen(false)}>
        <section className="dialog filter-dialog" onMouseDown={(event) => event.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="filter-title">
          <div className="dialog-header"><div><p className="eyebrow">{copy.narrow}</p><h2 id="filter-title">{copy.filterTitle}</h2></div><button className="icon-button" onClick={() => setFilterOpen(false)} aria-label={copy.close}><X size={20} /></button></div>
          <div className="filter-fields">
            <fieldset className="checkbox-field"><legend>{copy.direction}</legend><div className="checkbox-list">{(["mat", "iisi", "iad", "mad", "cs"] as const).map((major) => <label key={major}><input type="checkbox" checked={draftFilters.major.includes(major)} onChange={(event) => setDraftFilters({ ...draftFilters, major: event.target.checked ? [...draftFilters.major, major] : draftFilters.major.filter((value) => value !== major), subject: "" })} /> <span>{majorLabels[language][major]}</span></label>)}</div></fieldset>
            <label>{copy.subject}<select value={draftFilters.subject} onChange={(event) => setDraftFilters({ ...draftFilters, subject: event.target.value })}><option value="">{copy.anySubject}</option>{subjectOptions.map((subject) => <option key={subject}>{subject}</option>)}</select></label>
            <label>{copy.semester}<select value={draftFilters.semester} onChange={(event) => setDraftFilters({ ...draftFilters, semester: event.target.value })}><option value="">{copy.anySemester}</option>{Array.from({ length: 8 }, (_, index) => <option key={index + 1} value={index + 1}>{index + 1}</option>)}</select></label>
            <label>{copy.classType}<select value={draftFilters.classType} onChange={(event) => setDraftFilters({ ...draftFilters, classType: event.target.value })}><option value="">{copy.anyType}</option><option value="tutorial">{classTypeLabels[language].tutorial}</option><option value="labs">{classTypeLabels[language].labs}</option><option value="project">{classTypeLabels[language].project}</option></select></label>
            <label>{copy.haveGroup}<input value={draftFilters.groupHave} onChange={(event) => setDraftFilters({ ...draftFilters, groupHave: event.target.value })} placeholder="np. 12" /></label>
            <label>{copy.wantGroup}<input value={draftFilters.groupWant} onChange={(event) => setDraftFilters({ ...draftFilters, groupWant: event.target.value })} placeholder="np. 14, 15, 16" /></label>
          </div>
          <div className="dialog-actions"><button className="text-button" onClick={() => setDraftFilters(defaultFilters)}>{copy.clear}</button><button className="primary-button" onClick={applyFilters}>{copy.showResults}</button></div>
        </section>
      </div>}

      {selectedListing && <div className="modal-backdrop" onMouseDown={() => setSelectedListing(null)}>
        <section className="dialog detail-dialog" onMouseDown={(event) => event.stopPropagation()} role="dialog" aria-modal="true">
          <div className="dialog-header"><div className="card-tags"><span className="tag tag-major">{majorLabels[language][selectedListing.major]}</span><span className="tag tag-type">{classTypeLabels[language][selectedListing.classType]}</span></div><button className="icon-button" onClick={() => setSelectedListing(null)} aria-label="Zamknij"><X size={20} /></button></div>
          <h2>{selectedListing.semester}: {selectedListing.subject}</h2><div className="exchange-line large"><span className="group-pill have">{selectedListing.groupHave}</span><ArrowRight className="exchange-arrow" size={25} /><div className="wanted-groups">{selectedListing.groupWant.map((group) => <span className="group-pill want" key={group}>{group}</span>)}</div></div><p>{selectedListing.description}</p>
          <button className="primary-button full" onClick={() => requestExchange(selectedListing.id)}>{copy.interested}</button>
        </section>
      </div>}

      {addOpen && <div className="modal-backdrop" onMouseDown={() => setAddOpen(false)}>
        <section className="dialog detail-dialog" onMouseDown={(event) => event.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="add-title">
          <div className="dialog-header"><div><p className="eyebrow">{language === "pl" ? `Krok ${step} z 3` : `Step ${step} of 3`}</p><h2 id="add-title">{copy.newListing}</h2></div><button className="icon-button" onClick={() => setAddOpen(false)} aria-label={copy.close}><X size={20} /></button></div>
          <div className="stepper"><span className={step >= 1 ? "active" : ""}>1</span><i /><span className={step >= 2 ? "active" : ""}>2</span><i /><span className={step >= 3 ? "active" : ""}>3</span></div>
          {step === 1 && <div className="filter-fields"><label>{copy.direction}<select value={newListing.major} onChange={(event) => setNewListing({ ...newListing, major: event.target.value as Listing["major"] })}><option value="mat">{majorLabels[language].mat}</option><option value="iisi">{majorLabels[language].iisi}</option><option value="iad">{majorLabels[language].iad}</option><option value="mad">{majorLabels[language].mad}</option><option value="cs">{majorLabels[language].cs}</option></select></label><label>{copy.semester}<select value={newListing.semester} onChange={(event) => setNewListing({ ...newListing, semester: event.target.value })}>{Array.from({ length: 14 }, (_, index) => <option key={index + 1}>{index + 1}</option>)}</select></label></div>}
          {step === 2 && <div className="filter-fields"><label>{copy.subject}<input value={newListing.subject} onChange={(event) => setNewListing({ ...newListing, subject: event.target.value })} placeholder={copy.subjectPlaceholder} /></label><label>{copy.classType}<select value={newListing.classType} onChange={(event) => setNewListing({ ...newListing, classType: event.target.value as Listing["classType"] })}><option value="tutorial">{classTypeLabels[language].tutorial}</option><option value="labs">{classTypeLabels[language].labs}</option><option value="project">{classTypeLabels[language].project}</option></select></label></div>}
          {step === 3 && <div className="filter-fields"><label>{copy.haveGroup}<input value={newListing.groupHave} onChange={(event) => setNewListing({ ...newListing, groupHave: event.target.value })} placeholder="np. 12" required /></label><label>{copy.wantGroup}<input value={newListing.groupWant} onChange={(event) => setNewListing({ ...newListing, groupWant: event.target.value })} placeholder="np. 14, 15, 16" required />{newListing.groupWant && (!newListing.groupHave.trim() || !parseGroups(newListing.groupWant).length || parseGroups(newListing.groupWant).includes(newListing.groupHave.trim())) && <small className="field-error">{language === "pl" ? "Podaj różne grupy." : "Enter different groups."}</small>}</label></div>}
          <div className="dialog-actions"><button className="text-button" onClick={() => step === 1 ? setAddOpen(false) : setStep(step - 1)}>{step === 1 ? copy.cancelLabel : <><ChevronLeft size={17} /> {copy.backLabel}</>}</button>{step < 3 ? <button className="primary-button" disabled={step === 2 && !newListing.subject.trim()} onClick={() => setStep(step + 1)}>{copy.nextLabel} <ChevronRight size={17} /></button> : <button className="primary-button" disabled={!groupFormValid} onClick={async () => { try { const response = await fetch("/api/listings", { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` }, body: JSON.stringify({ major: newListing.major, semester: Number(newListing.semester), subject: newListing.subject.trim(), class_type: newListing.classType, group_have: newListing.groupHave.trim(), group_want: parseGroups(newListing.groupWant) }) }); const data = await response.json(); if (!response.ok) throw new Error(formatApiError(data.detail, language === "pl" ? "Nie udało się opublikować ogłoszenia." : "Could not publish the listing.")); await reloadListings(); setFilters(defaultFilters); setDraftFilters(defaultFilters); setAddOpen(false); setStep(1); setToast(language === "pl" ? "Ogłoszenie opublikowane." : "Listing published."); } catch (error) { setToast(error instanceof Error ? error.message : (language === "pl" ? "Nie udało się opublikować ogłoszenia." : "Could not publish the listing.")); } }}>{copy.publishLabel}</button>}</div>
        </section>
      </div>}

      {authMode && <div className="modal-backdrop" onMouseDown={() => setAuthMode(null)}>
        <section className="dialog auth-dialog" onMouseDown={(event) => event.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="auth-title">
          <div className="dialog-header"><div><p className="eyebrow">Spindel</p><h2 id="auth-title">{authMode === "login" ? copy.loginTitle : authMode === "register" ? copy.registerTitle : authMode === "reset-request" ? copy.resetTitle : authMode === "reset-confirm" ? copy.resetConfirmTitle : copy.resendTitle}</h2></div><button className="icon-button" onClick={() => setAuthMode(null)} aria-label={copy.close}><X size={20} /></button></div>
          {(authMode === "login" || authMode === "register") && <form className="filter-fields" onSubmit={submitAuth}>
            <label>{copy.email}<input type="email" required value={authForm.email} onChange={(event) => setAuthForm({ ...authForm, email: event.target.value })} placeholder="12345678@pw.edu.pl" /></label>
            {authMode === "register" && <label>{copy.indexNumber}<input required pattern="[0-9]{6}" value={authForm.indexNumber} onChange={(event) => setAuthForm({ ...authForm, indexNumber: event.target.value })} placeholder="123456" /></label>}
            <label>{copy.password}<input type="password" required minLength={8} value={authForm.password} onChange={(event) => setAuthForm({ ...authForm, password: event.target.value })} placeholder="Minimum 8 znaków" /></label>
            {authError && <small className="field-error">{authError}</small>}
            <button className="primary-button full" disabled={authBusy}>{authBusy ? copy.wait : authMode === "login" ? copy.loginTitle : copy.registerTitle}</button>
            {authMode === "login" && <div className="auth-links"><button type="button" className="text-button" onClick={() => openUtilityAuth("reset-request")}>{copy.forgotPassword}</button><button type="button" className="text-button" onClick={() => openUtilityAuth("resend-verification")}>{copy.resendLink}</button></div>}
          </form>}
          {authMode === "reset-request" || authMode === "resend-verification" ? <form className="filter-fields" onSubmit={submitUtilityAuth}>
            <p className="auth-help">{copy.emailHelp}</p>
            <label>{copy.email}<input type="email" required value={authForm.email} onChange={(event) => setAuthForm({ ...authForm, email: event.target.value })} placeholder="12345678@pw.edu.pl" /></label>
            {authError && <small className="field-error">{authError}</small>}
            <button className="primary-button full" disabled={authBusy}>{authBusy ? copy.wait : copy.send}</button>
          </form> : null}
          {authMode === "reset-confirm" && <form className="filter-fields" onSubmit={submitPasswordReset}>
            <p className="auth-help">{copy.resetHelp}</p>
            <label>{copy.newPassword}<input type="password" required minLength={8} value={authForm.password} onChange={(event) => setAuthForm({ ...authForm, password: event.target.value })} placeholder="Minimum 8 znaków" /></label>
            {authError && <small className="field-error">{authError}</small>}
            <button className="primary-button full" disabled={authBusy}>{authBusy ? copy.wait : copy.changePassword}</button>
          </form>}
        </section>
      </div>}

      {exchangeOpen && <div className="modal-backdrop" onMouseDown={() => setExchangeOpen(false)}>
        <section className="dialog exchange-dialog" onMouseDown={(event) => event.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="exchange-title">
          <div className="dialog-header"><div><p className="eyebrow">{copy.myListings}</p><h2 id="exchange-title">{copy.sent} / {copy.received}</h2></div><button className="icon-button" onClick={() => setExchangeOpen(false)} aria-label={copy.close}><X size={20} /></button></div>
          <div className="exchange-sections">
            <section><h3>{copy.sent} <span>{sentRequests.length}</span></h3>{sentRequests.length === 0 ? <p className="panel-empty">{copy.noSent}</p> : sentRequests.map((request) => <div className="exchange-row" key={`sent-${request.id}`}><div><strong>{requestTitle(request)}</strong><small>{request.status === "pending" ? (language === "pl" ? "Oczekuje na decyzję" : "Waiting for a decision") : request.status}</small>{request.owner_email && <small>{copy.contact}: {request.owner_email}</small>}</div></div>)}</section>
            <section><h3>{copy.received} <span>{receivedRequests.length}</span></h3>{receivedRequests.length === 0 ? <p className="panel-empty">{copy.noReceived}</p> : receivedRequests.map((request) => <div className="exchange-row" key={`received-${request.id}`}><div><strong>{requestTitle(request)}</strong><small>{request.status === "pending" ? (language === "pl" ? "Nowe zainteresowanie" : "New interest") : request.status}</small>{request.requester_email && <small>{copy.contact}: {request.requester_email}</small>}</div>{request.status === "pending" && <div className="row-actions"><button className="primary-button compact" disabled={exchangeBusy} onClick={() => exchangeAction(request.id, "confirm")}>{copy.confirm}</button><button className="text-button" disabled={exchangeBusy} onClick={() => exchangeAction(request.id, "reject")}>{copy.reject}</button></div>}</div>)}</section>
            <section><h3>{copy.completed} <span>{completedRequests.length}</span></h3>{completedRequests.length === 0 ? <p className="panel-empty">{copy.noCompleted}</p> : completedRequests.map((request) => <div className="exchange-row" key={`completed-${request.id}`}><div><strong>{requestTitle(request)}</strong><small>{language === "pl" ? "Wymiana potwierdzona" : "Exchange confirmed"}</small>{request.requester_email && <small>{copy.contact}: {request.requester_email}</small>}{request.owner_email && <small>{copy.contact}: {request.owner_email}</small>}</div></div>)}</section>
            <section><h3>{copy.myListings} <span>{myListings.length}</span></h3>{myListings.length === 0 ? <p className="panel-empty">{copy.noListings}</p> : myListings.map((listing) => <div className="exchange-row" key={`listing-${listing.id}`}><div><strong>{listing.subject} · gr. {listing.groupHave} → {listing.groupWant.join(", ")}</strong><small>{listing.status}</small></div>{(listing.status === "active" || listing.status === "pending") && <button className="text-button" disabled={exchangeBusy} onClick={() => cancelListing(listing.id)}>{copy.cancel}</button>}</div>)}</section>
          </div>
          <p className="panel-note">Numery ogłoszeń pozostają widoczne także po zakończeniu wymiany, aby historia była czytelna.</p>
        </section>
      </div>}

      {toast && <div className="toast" role="status"><span>{toast}</span><button onClick={() => setToast("")} aria-label="Zamknij komunikat"><X size={16} /></button></div>}
      <footer className="site-footer"><span>{language === "pl" ? "Wymiana grup dla studentów MiNI PW" : "Group exchange for MiNI PW students"}</span><span><a href="https://maciejwelpa.pl">Kontakt</a><a href="/regulamin.html">Regulamin</a><a href="/polityka-prywatnosci.html">Polityka prywatności</a><span>Spindel · maciejwelpa.pl</span></span></footer>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
