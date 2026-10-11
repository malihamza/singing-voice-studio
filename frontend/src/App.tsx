import { useCallback, useEffect, useRef, useState } from "react";
import {
  AudioLines,
  BookOpen,
  Check,
  ChevronRight,
  CircleUserRound,
  Clock3,
  Cpu,
  Download,
  FolderClock,
  Library,
  Menu,
  Mic2,
  Moon,
  Music2,
  PlayCircle,
  Plus,
  Settings,
  Sparkles,
  Sun,
  Upload,
  WandSparkles,
  X,
} from "lucide-react";
import "./App.css";

type Page = "create" | "profiles" | "guide" | "jobs" | "library" | "settings";
type Profile = {
  id: string;
  name: string;
  status: string;
  created: string;
  clip_count: number;
  dataset_seconds: number;
  reference_url: string;
  training?: { status: string; step: number; total: number };
};
type Job = {
  id: string;
  profile_id: string;
  source_method: string;
  quality_mode: string;
  status: string;
  created: string;
  overall_percent: number;
  stage_percent: number;
  active_stage?: number;
  completed_stages?: number;
  detail: string;
  logs: string;
  result?: string;
  error?: string;
};
type System = {
  device: string;
  mps: boolean;
  local_only: boolean;
  profiles: number;
  active_jobs: number;
};
type TrainingPrompt = {
  kind: "Speak" | "Sing";
  title: string;
  text: string;
  direction: string;
  target: string;
  note?: number;
};

const trainingPrompts: TrainingPrompt[] = [
  {
    kind: "Speak",
    title: "Natural English speech",
    text: "Today I am recording my natural voice. I will speak clearly, calmly, and without forcing any sound.",
    direction:
      "Use your normal conversational voice. Do not perform or imitate anyone.",
    target: "12–18 seconds",
  },
  {
    kind: "Speak",
    title: "Natural storytelling",
    text: "I opened the window this morning, took a slow breath, and listened to the city waking up around me.",
    direction:
      "Tell the line as if you are speaking to a friend. Keep a relaxed, natural pace.",
    target: "12–18 seconds",
  },
  {
    kind: "Speak",
    title: "Consonant coverage",
    text: "Bright paper, gentle thunder, silver roads, quiet gardens, warm voices, and clear morning air.",
    direction: "Keep every consonant clear without becoming theatrical.",
    target: "10–15 seconds",
  },
  {
    kind: "Sing",
    title: "Sustained vowels",
    text: "Aaah — Eeeh — Oooh — Aaay — Oooh",
    direction:
      "Hold each vowel for 3–4 seconds on one comfortable middle note. Take a breath between vowels.",
    target: "18–25 seconds",
    note: 220,
  },
  {
    kind: "Sing",
    title: "Comfortable low range",
    text: "The evening settles softly, and I am finding my way home.",
    direction:
      "Create a simple melody near the lower comfortable part of your range. Never push downward.",
    target: "12–18 seconds",
    note: 174.61,
  },
  {
    kind: "Sing",
    title: "Comfortable middle range",
    text: "Morning light is calling, every open road is shining.",
    direction: "Sing with your everyday tone and a smooth, connected melody.",
    target: "12–18 seconds",
    note: 220,
  },
  {
    kind: "Sing",
    title: "Comfortable higher range",
    text: "I can see the new horizon, rising brightly over me.",
    direction:
      "Move toward your comfortable high range without shouting or straining.",
    target: "12–18 seconds",
    note: 261.63,
  },
  {
    kind: "Sing",
    title: "Gentle middle melody",
    text: "Every little moment carries something new for me.",
    direction: "Sing a smooth melody in the middle of your comfortable range.",
    target: "10–16 seconds",
    note: 220,
  },
  {
    kind: "Sing",
    title: "Expressive phrase",
    text: "Along the road I found a dream that waited there for me.",
    direction: "Begin gently and let the phrase grow slightly stronger.",
    target: "10–16 seconds",
    note: 196,
  },
  {
    kind: "Sing",
    title: "Ascending movement",
    text: "One — two — three — four — five — four — three — two — one",
    direction:
      "Sing upward for the first five numbers and return downward. Stay in an easy range.",
    target: "10–15 seconds",
    note: 196,
  },
  {
    kind: "Sing",
    title: "Soft delivery",
    text: "Stay near, quiet night, carry this little song with you.",
    direction:
      "Sing softly but clearly. Avoid whispering; preserve a stable pitch.",
    target: "12–18 seconds",
    note: 196,
  },
  {
    kind: "Sing",
    title: "Stronger delivery",
    text: "I will carry on with courage, I will let my true voice rise.",
    direction:
      "Use confident energy without yelling or clipping the microphone.",
    target: "12–18 seconds",
    note: 220,
  },
  {
    kind: "Sing",
    title: "Long connected phrase",
    text: "Across the open sky I follow every color of the changing light.",
    direction:
      "Use legato: connect the words smoothly with as few breaks as comfortable.",
    target: "12–18 seconds",
    note: 220,
  },
  {
    kind: "Sing",
    title: "Short rhythmic phrase",
    text: "Step by step, beat by beat, moving with the sound beneath my feet.",
    direction: "Use a quicker rhythm while keeping every word understandable.",
    target: "10–15 seconds",
    note: 220,
  },
  {
    kind: "Sing",
    title: "Rhythmic articulation",
    text: "Feel the rhythm, follow the motion, let every word land clearly.",
    direction: "Sing with a light rhythmic pulse and clear consonants.",
    target: "12–18 seconds",
    note: 220,
  },
  {
    kind: "Sing",
    title: "Dynamic change",
    text: "Start with a whisper of light, then let the whole world hear.",
    direction:
      "Start gently and gradually become stronger, while keeping the same microphone distance.",
    target: "12–18 seconds",
    note: 196,
  },
  {
    kind: "Sing",
    title: "Open vowel melody",
    text: "La — la — laa, Maa — mee — moo, Na — nay — noo",
    direction:
      "Create a relaxed melody that moves through three or four comfortable notes.",
    target: "15–22 seconds",
    note: 220,
  },
  {
    kind: "Sing",
    title: "Emotional warmth",
    text: "Even when the road is distant, I remember where my heart belongs.",
    direction: "Sing warmly and sincerely; do not exaggerate vibrato.",
    target: "12–18 seconds",
    note: 196,
  },
  {
    kind: "Sing",
    title: "Clean sustained ending",
    text: "I am home — oooh — I am home — aaah.",
    direction:
      "Hold each final vowel steadily, then release naturally without cutting it off.",
    target: "14–20 seconds",
    note: 220,
  },
  {
    kind: "Sing",
    title: "Your natural freestyle",
    text: "Sing an original line or hum a melody that feels completely natural to you.",
    direction:
      "Use your own words and melody. Cover a part of your voice not represented above.",
    target: "15–25 seconds",
    note: 220,
  },
];

const nav: { id: Page; label: string; icon: typeof Music2 }[] = [
  { id: "create", label: "Create", icon: WandSparkles },
  { id: "profiles", label: "Voice profiles", icon: CircleUserRound },
  { id: "guide", label: "Recording guide", icon: BookOpen },
  { id: "jobs", label: "Jobs", icon: FolderClock },
  { id: "library", label: "Audio library", icon: Library },
  { id: "settings", label: "Settings", icon: Settings },
];

async function api<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail || "Request failed");
  }
  return response.json();
}

function time(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes}:${String(rest).padStart(2, "0")}`;
}

function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

function Empty({
  icon: Icon,
  title,
  copy,
  action,
}: {
  icon: typeof Music2;
  title: string;
  copy: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Icon size={25} />
      </div>
      <h3>{title}</h3>
      <p>{copy}</p>
      {action}
    </div>
  );
}

function App() {
  const [page, setPage] = useState<Page>("create");
  const [dark, setDark] = useState(
    localStorage.getItem("studio-theme") === "dark",
  );
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [system, setSystem] = useState<System | null>(null);
  const [toast, setToast] = useState("");

  const refresh = useCallback(async () => {
    const [p, j, s] = await Promise.all([
      api<Profile[]>("/api/profiles"),
      api<Job[]>("/api/jobs"),
      api<System>("/api/system"),
    ]);
    setProfiles(p);
    setJobs(j);
    setSystem(s);
  }, []);
  // Data is loaded from the local API after the shell mounts.
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    refresh().catch((e) => setToast(e.message));
  }, [refresh]);
  useEffect(() => {
    if (
      !profiles.some((profile) =>
        ["queued", "running"].includes(profile.training?.status || ""),
      )
    )
      return;
    const timer = setInterval(() => refresh().catch(() => {}), 5000);
    return () => clearInterval(timer);
  }, [profiles, refresh]);
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("studio-theme", dark ? "dark" : "light");
  }, [dark]);
  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(""), 4500);
      return () => clearTimeout(t);
    }
  }, [toast]);

  const go = (next: Page) => {
    setPage(next);
    setMobileOpen(false);
    refresh().catch(() => {});
  };
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <AudioLines size={22} />
          </div>
          <div>
            <strong>Vocal Studio</strong>
            <span>Local AI workspace</span>
          </div>
        </div>
        <nav>
          {nav.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={page === id ? "active" : ""}
              onClick={() => go(id)}
            >
              <Icon size={19} />
              <span>{label}</span>
              {page === id && <ChevronRight size={16} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="system-card">
          <div className="system-title">
            <span className="live-dot" />
            System ready
          </div>
          <div>
            <Cpu size={15} />
            {system?.device || "Checking…"}
          </div>
          <div>
            <Sparkles size={15} />
            {system?.profiles || 0} voice profiles
          </div>
          <div>
            <Clock3 size={15} />
            {system?.active_jobs || 0} active jobs
          </div>
        </div>
        <button className="theme-button" onClick={() => setDark(!dark)}>
          {dark ? <Sun size={18} /> : <Moon size={18} />}
          <span>{dark ? "Light" : "Dark"} appearance</span>
        </button>
        <div className="local-note">
          <span>●</span> Files stay on this Mac
        </div>
      </aside>
      {mobileOpen && (
        <button className="scrim" onClick={() => setMobileOpen(false)} />
      )}
      <main>
        <header>
          <button className="mobile-menu" onClick={() => setMobileOpen(true)}>
            <Menu />
          </button>
          <div>
            <span className="eyebrow">MY SINGING VOICE</span>
            <h1>{nav.find((n) => n.id === page)?.label}</h1>
          </div>
          <div className="header-actions">
            <Badge tone="success">● MPS ready</Badge>
            <button className="icon-button" onClick={() => setDark(!dark)}>
              {dark ? <Sun /> : <Moon />}
            </button>
          </div>
        </header>
        <div className="content">
          {page === "create" && (
            <Create
              profiles={profiles}
              onNeedProfile={() => setPage("profiles")}
              onJob={(job) => {
                setJobs((v) => [job, ...v]);
                setPage("jobs");
              }}
              onError={setToast}
            />
          )}
          {page === "profiles" && (
            <Profiles
              profiles={profiles}
              refresh={refresh}
              onError={setToast}
            />
          )}
          {page === "guide" && <RecordingGuide />}
          {page === "jobs" && (
            <Jobs jobs={jobs} setJobs={setJobs} onError={setToast} />
          )}
          {page === "library" && (
            <LibraryPage jobs={jobs.filter((j) => j.status === "complete")} />
          )}
          {page === "settings" && <SettingsPage system={system} />}
        </div>
      </main>
      {toast && (
        <div className="toast">
          <X size={17} />
          {toast}
        </div>
      )}
    </div>
  );
}

function Create({
  profiles,
  onNeedProfile,
  onJob,
  onError,
}: {
  profiles: Profile[];
  onNeedProfile: () => void;
  onJob: (j: Job) => void;
  onError: (s: string) => void;
}) {
  const [profile, setProfile] = useState(profiles[0]?.id || "");
  const [method, setMethod] = useState("Finished song");
  const [quality, setQuality] = useState("Balanced");
  const [song, setSong] = useState<File | null>(null);
  const [vocal, setVocal] = useState<File | null>(null);
  const [instrumental, setInstrumental] = useState<File | null>(null);
  const [permission, setPermission] = useState(false);
  const [busy, setBusy] = useState(false);
  const profileId = profile || profiles[0]?.id || "";
  const selected = profiles.find((p) => p.id === profileId);
  const ready =
    profileId &&
    permission &&
    (method === "Finished song"
      ? song
      : method === "Vocal only"
        ? vocal
        : vocal && instrumental);
  const submit = async () => {
    if (!ready) return;
    setBusy(true);
    const form = new FormData();
    form.set("profile_id", profileId);
    form.set("source_method", method);
    form.set("quality_mode", quality);
    form.set("permission", "true");
    if (song) form.set("song", song);
    if (vocal) form.set("vocal", vocal);
    if (instrumental) form.set("instrumental", instrumental);
    try {
      onJob(await api<Job>("/api/jobs", { method: "POST", body: form }));
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  if (!profiles.length)
    return (
      <Empty
        icon={CircleUserRound}
        title="Create your first voice profile"
        copy="A profile securely stores your reference recording so you can reuse it for every song."
        action={
          <button className="primary" onClick={onNeedProfile}>
            Create voice profile
          </button>
        }
      />
    );
  return (
    <>
      <section className="welcome">
        <div>
          <Badge>NEW GENERATION</Badge>
          <h2>
            Turn a performance into <span>your voice.</span>
          </h2>
          <p>
            Select a saved voice, provide the cleanest source available, and let
            the local production pipeline handle the rest.
          </p>
        </div>
        <div className="wave-art">
          <i />
          <i />
          <i />
          <i />
          <i />
          <i />
          <i />
          <i />
          <i />
        </div>
      </section>
      <div className="create-grid">
        <section className="panel">
          <div className="panel-head">
            <div className="step-number">1</div>
            <div>
              <h3>Voice identity</h3>
              <p>Choose the voice that will perform.</p>
            </div>
          </div>
          <div className="profile-picker">
            {profiles.map((p) => (
              <button
                key={p.id}
                className={profileId === p.id ? "selected" : ""}
                onClick={() => setProfile(p.id)}
              >
                <div className="avatar">{p.name.slice(0, 2).toUpperCase()}</div>
                <div>
                  <strong>{p.name}</strong>
                  <span>
                    {p.status === "trained"
                      ? "Fine-tuned singing model"
                      : "Zero-shot profile"}
                  </span>
                </div>
                {profileId === p.id && <Check />}
              </button>
            ))}
          </div>
          {selected && (
            <div className="selection-note">
              <Sparkles size={17} />
              <span>
                {selected.status === "trained"
                  ? "Custom trained checkpoint will be used automatically."
                  : "Uses the saved canonical reference. Add singing clips under Voice profiles for stronger identity."}
              </span>
            </div>
          )}
        </section>
        <section className="panel">
          <div className="panel-head">
            <div className="step-number">2</div>
            <div>
              <h3>Performance source</h3>
              <p>Cleaner source audio produces better conversion.</p>
            </div>
          </div>
          <div className="segment">
            {["Finished song", "Vocal + instrumental stems", "Vocal only"].map(
              (x) => (
                <button
                  className={method === x ? "selected" : ""}
                  onClick={() => setMethod(x)}
                  key={x}
                >
                  {x}
                </button>
              ),
            )}
          </div>
          {method === "Finished song" && (
            <Dropzone
              title="Finished song"
              hint="WAV, FLAC, M4A or MP3"
              file={song}
              setFile={setSong}
            />
          )}
          {method !== "Finished song" && (
            <Dropzone
              title="Isolated lead vocal"
              hint="Dry lead vocal works best"
              file={vocal}
              setFile={setVocal}
            />
          )}
          {method === "Vocal + instrumental stems" && (
            <Dropzone
              title="Matching instrumental"
              hint="Same start time and duration"
              file={instrumental}
              setFile={setInstrumental}
            />
          )}
        </section>
        <section className="panel full">
          <div className="panel-head">
            <div className="step-number">3</div>
            <div>
              <h3>Production quality</h3>
              <p>Choose the time and quality balance.</p>
            </div>
          </div>
          <div className="quality-grid">
            {[
              ["Fast", "12 steps", "Quick previews · 8s reference"],
              ["Balanced", "24 steps", "Recommended · 12s reference"],
              [
                "Best Quality",
                "40 steps",
                "Maximum refinement · 20s reference",
              ],
            ].map(([name, meta, copy]) => (
              <button
                className={quality === name ? "selected" : ""}
                onClick={() => setQuality(name)}
                key={name}
              >
                <strong>{name}</strong>
                <span>{meta}</span>
                <small>{copy}</small>
                {quality === name && <Check />}
              </button>
            ))}
          </div>
          <label className="consent">
            <input
              type="checkbox"
              checked={permission}
              onChange={(e) => setPermission(e.target.checked)}
            />
            <span>
              <strong>Authorized use</strong>I own this voice and have
              permission to transform the uploaded audio.
            </span>
          </label>
          <button
            className="generate"
            disabled={!ready || busy}
            onClick={submit}
          >
            {busy ? (
              "Creating job…"
            ) : (
              <>
                Generate my audio <ChevronRight />
              </>
            )}
          </button>
        </section>
      </div>
    </>
  );
}

function Dropzone({
  title,
  hint,
  file,
  setFile,
}: {
  title: string;
  hint: string;
  file: File | null;
  setFile: (f: File | null) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <button
      className={`dropzone ${file ? "has-file" : ""}`}
      onClick={() => input.current?.click()}
    >
      <input
        ref={input}
        hidden
        type="file"
        accept="audio/*"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      {file ? (
        <>
          <div className="file-icon">
            <Music2 />
          </div>
          <div>
            <strong>{file.name}</strong>
            <span>
              {(file.size / 1024 / 1024).toFixed(1)} MB · Click to replace
            </span>
          </div>
          <Check className="file-check" />
        </>
      ) : (
        <>
          <Upload />
          <div>
            <strong>{title}</strong>
            <span>{hint}</span>
          </div>
        </>
      )}
    </button>
  );
}

function Profiles({
  profiles,
  refresh,
  onError,
}: {
  profiles: Profile[];
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [showNew, setShowNew] = useState(false);
  const [selectedId, setSelectedId] = useState("");
  const selected =
    profiles.find((profile) => profile.id === selectedId) ||
    profiles[0] ||
    null;
  return (
    <div className="two-pane">
      <section>
        <div className="page-intro">
          <div>
            <h2>Your voices</h2>
            <p>
              Reusable identities for zero-shot and fine-tuned singing
              conversion.
            </p>
          </div>
          <button className="primary" onClick={() => setShowNew(true)}>
            <Plus />
            New profile
          </button>
        </div>
        <div className="profile-list">
          {profiles.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelectedId(p.id)}
              className={selected?.id === p.id ? "selected" : ""}
            >
              <div className="avatar large">
                {p.name.slice(0, 2).toUpperCase()}
              </div>
              <div>
                <strong>{p.name}</strong>
                <span>
                  {p.status === "trained" ? "Trained voice" : "Zero-shot voice"}{" "}
                  · {p.clip_count} training clips
                </span>
              </div>
              <Badge tone={p.status === "trained" ? "success" : "neutral"}>
                {p.status}
              </Badge>
            </button>
          ))}
        </div>
        {!profiles.length && (
          <Empty
            icon={Mic2}
            title="No voice profiles yet"
            copy="Record a clean reference to create one."
          />
        )}
      </section>
      <aside className="detail-pane">
        {selected ? (
          <ProfileDetail
            profile={selected}
            refresh={refresh}
            onError={onError}
          />
        ) : (
          <Empty
            icon={CircleUserRound}
            title="Select a voice"
            copy="Profile details will appear here."
          />
        )}
      </aside>
      {showNew && (
        <NewProfile
          close={() => setShowNew(false)}
          done={async () => {
            setShowNew(false);
            await refresh();
          }}
          onError={onError}
        />
      )}
    </div>
  );
}

function NewProfile({
  close,
  done,
  onError,
}: {
  close: () => void;
  done: () => void;
  onError: (s: string) => void;
}) {
  const [name, setName] = useState("My Voice");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const create = async () => {
    if (!file) return;
    setBusy(true);
    const form = new FormData();
    form.set("name", name);
    form.set("reference", file);
    try {
      await api("/api/profiles", { method: "POST", body: form });
      done();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="modal-wrap">
      <button className="modal-scrim" onClick={close} />
      <div className="modal">
        <button className="modal-close" onClick={close}>
          <X />
        </button>
        <Badge>VOICE PROFILE</Badge>
        <h2>Create your reusable voice</h2>
        <p>
          Start with one clean 10–20 second reference. You can add singing clips
          and fine-tune later.
        </p>
        <label className="field">
          <span>Profile name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <Recorder onFile={setFile} onError={onError} />
        <div className="or">
          <span>or upload a recording</span>
        </div>
        <Dropzone
          title="Voice reference"
          hint="5–30 seconds · quiet and dry"
          file={file}
          setFile={setFile}
        />
        <div className="tip">
          <Mic2 />
          <span>
            Speak naturally, then sustain “aa”, “ee”, and “oo”. Finish with one
            comfortable sung phrase.
          </span>
        </div>
        <button
          className="primary wide"
          disabled={!file || busy}
          onClick={create}
        >
          {busy ? "Preparing voice…" : "Create voice profile"}
        </button>
      </div>
    </div>
  );
}

function Recorder({
  onFile,
  onError,
}: {
  onFile: (file: File) => void;
  onError: (message: string) => void;
}) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [level, setLevel] = useState(0);
  const media = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const chunks = useRef<Blob[]>([]);
  const stop = () =>
    media.current?.state === "recording" && media.current.stop();
  const start = async () => {
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: false,
        },
      });
      const recorder = new MediaRecorder(stream.current);
      chunks.current = [];
      setSeconds(0);
      recorder.ondataavailable = (e) => {
        if (e.data.size) chunks.current.push(e.data);
      };
      recorder.onstop = () => {
        const type = recorder.mimeType || "audio/webm";
        onFile(
          new File(
            [new Blob(chunks.current, { type })],
            "recorded-reference.webm",
            { type },
          ),
        );
        stream.current?.getTracks().forEach((t) => t.stop());
        if (timer.current) clearInterval(timer.current);
        setRecording(false);
        setLevel(0);
      };
      recorder.start(250);
      media.current = recorder;
      setRecording(true);
      const audio = new AudioContext();
      const source = audio.createMediaStreamSource(stream.current);
      const analyser = audio.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      const values = new Uint8Array(analyser.frequencyBinCount);
      timer.current = setInterval(() => {
        setSeconds((s) => {
          if (s >= 29) {
            stop();
            return s;
          }
          return s + 1;
        });
        analyser.getByteFrequencyData(values);
        setLevel(
          Math.min(
            100,
            Math.round(
              values.reduce((a, b) => a + b, 0) / values.length / 1.25,
            ),
          ),
        );
      }, 1000);
    } catch (e) {
      onError(`Microphone unavailable: ${(e as Error).message}`);
    }
  };
  useEffect(
    () => () => {
      stream.current?.getTracks().forEach((t) => t.stop());
      if (timer.current) clearInterval(timer.current);
    },
    [],
  );
  return (
    <div className={`recorder ${recording ? "recording" : ""}`}>
      <div className="recorder-copy">
        <div className="record-dot" />
        <div>
          <strong>
            {recording ? "Recording your voice…" : "Record in this browser"}
          </strong>
          <span>
            {recording
              ? `${seconds}s / 30s · Keep peaks below red`
              : "Quiet room · 15–25 cm from microphone"}
          </span>
        </div>
      </div>
      <div className="meter">
        <i style={{ width: `${level}%` }} />
      </div>
      <button
        className={recording ? "stop-record" : "start-record"}
        onClick={recording ? stop : start}
      >
        {recording ? "Stop & use recording" : "Start recording"}
      </button>
    </div>
  );
}

function ProfileDetail({
  profile,
  refresh,
  onError,
}: {
  profile: Profile;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [guided, setGuided] = useState(false);
  const clips = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy(true);
    const form = new FormData();
    Array.from(files).forEach((f) => form.append("clips", f));
    try {
      await api(`/api/profiles/${profile.id}/clips`, {
        method: "POST",
        body: form,
      });
      await refresh();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const train = async () => {
    setBusy(true);
    const form = new FormData();
    form.set("max_steps", "500");
    try {
      await api(`/api/profiles/${profile.id}/train`, {
        method: "POST",
        body: form,
      });
      await refresh();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const readiness = Math.min(100, (profile.dataset_seconds / 300) * 100);
  return (
    <>
      <div className="profile-hero">
        <div className="avatar xl">
          {profile.name.slice(0, 2).toUpperCase()}
        </div>
        <h2>{profile.name}</h2>
        <Badge tone={profile.status === "trained" ? "success" : "neutral"}>
          {profile.status}
        </Badge>
        <audio controls src={profile.reference_url} />
      </div>
      <div className="metric-row">
        <div>
          <strong>{profile.clip_count}</strong>
          <span>clips</span>
        </div>
        <div>
          <strong>{time(profile.dataset_seconds)}</strong>
          <span>training audio</span>
        </div>
        <div>
          <strong>{profile.status === "trained" ? "Ready" : "Draft"}</strong>
          <span>model</span>
        </div>
      </div>
      <div className="readiness">
        <div>
          <span>Training readiness</span>
          <strong>{Math.round(readiness)}%</strong>
        </div>
        <div className="bar">
          <i style={{ width: `${readiness}%` }} />
        </div>
        <p>
          {profile.dataset_seconds < 300
            ? `${time(300 - profile.dataset_seconds)} more clean singing required for the five-minute minimum.`
            : "Dataset is ready for an initial fine-tune."}
        </p>
      </div>
      <button
        className="primary wide guided-button"
        onClick={() => setGuided(true)}
      >
        <Mic2 />
        Start guided recording session
      </button>
      <input
        ref={input}
        hidden
        multiple
        type="file"
        accept="audio/*"
        onChange={(e) => clips(e.target.files)}
      />
      <button
        className="secondary wide"
        onClick={() => input.current?.click()}
        disabled={busy}
      >
        <Upload />
        Upload existing training clips
      </button>
      <button
        className="primary wide"
        onClick={train}
        disabled={
          profile.dataset_seconds < 300 ||
          busy ||
          profile.training?.status === "running"
        }
      >
        <Sparkles />
        {profile.training?.status === "running"
          ? `Training ${profile.training.step}/${profile.training.total}`
          : "Train singing voice"}
      </button>
      <div className="mini-guide">
        <strong>How to prepare this voice</strong>
        <span>
          Use Guided Recording for original speech and singing prompts with
          range coaching. Complete all 20 prompts, then repeat weaker sections
          until you have at least five minutes; 10–30 minutes gives a stronger
          model.
        </span>
      </div>
      {guided && (
        <GuidedSession
          profile={profile}
          close={() => setGuided(false)}
          refresh={refresh}
          onError={onError}
        />
      )}
    </>
  );
}

function GuidedSession({
  profile,
  close,
  refresh,
  onError,
}: {
  profile: Profile;
  close: () => void;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [index, setIndex] = useState(0);
  const [take, setTake] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(0);
  const prompt = trainingPrompts[index];
  const preview = take ? URL.createObjectURL(take) : "";
  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );
  const playNote = () => {
    if (!prompt.note) return;
    const context = new AudioContext();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.frequency.value = prompt.note;
    oscillator.type = "sine";
    gain.gain.setValueAtTime(0.12, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 1.2);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + 1.2);
  };
  const save = async () => {
    if (!take) return;
    setSaving(true);
    const form = new FormData();
    form.append("clips", take, `guided-${index + 1}.webm`);
    try {
      await api(`/api/profiles/${profile.id}/clips`, {
        method: "POST",
        body: form,
      });
      setSaved((n) => n + 1);
      setTake(null);
      if (index < trainingPrompts.length - 1) setIndex((i) => i + 1);
      await refresh();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };
  const move = (amount: number) => {
    setTake(null);
    setIndex((i) =>
      Math.max(0, Math.min(trainingPrompts.length - 1, i + amount)),
    );
  };
  return (
    <div className="modal-wrap guided-wrap">
      <button className="modal-scrim" onClick={close} />
      <div className="modal guided-modal">
        <button className="modal-close" onClick={close}>
          <X />
        </button>
        <div className="session-top">
          <div>
            <Badge>
              {prompt.kind} · Prompt {index + 1} of {trainingPrompts.length}
            </Badge>
            <h2>Build {profile.name}'s singing dataset</h2>
          </div>
          <div className="session-saved">
            <strong>{saved}</strong>
            <span>saved this session</span>
          </div>
        </div>
        <div className="session-progress">
          <i
            style={{
              width: `${((index + 1) / trainingPrompts.length) * 100}%`,
            }}
          />
        </div>
        <div className="prompt-card">
          <div className="prompt-meta">
            <Badge tone={prompt.kind === "Sing" ? "success" : "neutral"}>
              {prompt.kind}
            </Badge>
            <span>Target: {prompt.target}</span>
          </div>
          <h3>{prompt.title}</h3>
          <blockquote>{prompt.text}</blockquote>
          <div className="direction">
            <BookOpen />
            <span>{prompt.direction}</span>
          </div>
          {prompt.note && (
            <button className="note-button" onClick={playNote}>
              <PlayCircle />
              Play a comfortable starting note
            </button>
          )}
        </div>
        <Recorder onFile={setTake} onError={onError} />
        {take && (
          <div className="take-review">
            <div>
              <strong>Review this take</strong>
              <span>
                Listen for clipping, room noise, strain, or music in the
                background.
              </span>
            </div>
            <audio controls src={preview} />
            <div className="take-actions">
              <button className="secondary" onClick={() => setTake(null)}>
                Record again
              </button>
              <button className="primary" onClick={save} disabled={saving}>
                {saving ? (
                  "Saving…"
                ) : (
                  <>
                    <Check />
                    Save & next prompt
                  </>
                )}
              </button>
            </div>
          </div>
        )}
        <div className="session-nav">
          <button onClick={() => move(-1)} disabled={index === 0}>
            ← Previous
          </button>
          <button
            onClick={() => move(1)}
            disabled={index === trainingPrompts.length - 1}
          >
            Skip prompt →
          </button>
        </div>
        <p className="session-note">
          These are original practice lines created for this local training
          workflow—not copyrighted song lyrics. Sing them with any simple melody
          that feels comfortable.
        </p>
      </div>
    </div>
  );
}

function RecordingGuide() {
  return (
    <div className="guide-layout">
      <section className="guide-hero">
        <Badge>RECORDING COACH</Badge>
        <h2>A great model starts before you press record.</h2>
        <p>
          Follow this sequence to capture a balanced voice identity without
          strain or room contamination.
        </p>
      </section>
      <div className="guide-steps">
        {[
          [
            "01",
            "Prepare the room",
            "Choose the quietest room available. Close windows, silence fans, move away from bare walls, and wear headphones so no music reaches the microphone.",
          ],
          [
            "02",
            "Set microphone distance",
            "Stay 15–25 cm from the microphone and slightly off-axis. Keep the same position. Peaks should be strong but never clip or turn red.",
          ],
          [
            "03",
            "Capture natural speech",
            "Record calm conversational speech. Include different consonants and sustain “aa”, “ee”, and “oo” for several seconds.",
          ],
          [
            "04",
            "Cover your singing range",
            "Record comfortable low, middle, and high phrases. Include soft and strong delivery, long notes, legato, and faster lyrics. Never strain.",
          ],
          [
            "05",
            "Keep clips clean",
            "Make clips 5–20 seconds, leave a short silence at each end, and avoid reverb, pitch effects, compression, background music, or doubled vocals.",
          ],
        ].map(([n, t, c]) => (
          <article key={n}>
            <span>{n}</span>
            <div>
              <h3>{t}</h3>
              <p>{c}</p>
            </div>
          </article>
        ))}
      </div>
      <section className="prompt-board">
        <div>
          <h3>Suggested 15-minute session</h3>
          <p>
            Use this balanced collection for a strong first trained profile.
          </p>
        </div>
        <div className="prompt-grid">
          {[
            ["2 min", "Natural speech"],
            ["2 min", "Sustained vowels"],
            ["3 min", "Low and mid melodies"],
            ["3 min", "Higher comfortable melodies"],
            ["3 min", "Clear lyrical phrases"],
            ["2 min", "Soft and strong dynamics"],
          ].map(([a, b]) => (
            <div key={b}>
              <strong>{a}</strong>
              <span>{b}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Jobs({
  jobs,
  setJobs,
  onError,
}: {
  jobs: Job[];
  setJobs: React.Dispatch<React.SetStateAction<Job[]>>;
  onError: (s: string) => void;
}) {
  const [selected, setSelected] = useState(jobs[0]?.id || "");
  const current = jobs.find((j) => j.id === selected) || jobs[0];
  const currentId = current?.id;
  const currentStatus = current?.status;
  useEffect(() => {
    if (!currentId || !["queued", "running"].includes(currentStatus || ""))
      return;
    const stream = new EventSource(`/api/jobs/${currentId}/events`);
    stream.onmessage = (e) => {
      const next = JSON.parse(e.data);
      setJobs((previous) => previous.map((j) => (j.id === next.id ? next : j)));
      if (["complete", "failed"].includes(next.status)) stream.close();
    };
    stream.onerror = () => stream.close();
    return () => stream.close();
  }, [currentId, currentStatus, setJobs]);
  return (
    <div className="jobs-layout">
      <section>
        <div className="page-intro">
          <div>
            <h2>Production jobs</h2>
            <p>Every local generation and its recoverable status.</p>
          </div>
        </div>
        <div className="job-list">
          {jobs.map((j) => (
            <button
              key={j.id}
              className={current?.id === j.id ? "selected" : ""}
              onClick={() => setSelected(j.id)}
            >
              <div className={`job-icon ${j.status}`}>
                <Music2 />
              </div>
              <div>
                <strong>{j.source_method}</strong>
                <span>
                  {j.quality_mode} · {new Date(j.created).toLocaleString()}
                </span>
              </div>
              <Badge
                tone={
                  j.status === "complete"
                    ? "success"
                    : j.status === "failed"
                      ? "danger"
                      : "neutral"
                }
              >
                {j.status}
              </Badge>
            </button>
          ))}
        </div>
        {!jobs.length && (
          <Empty
            icon={FolderClock}
            title="No jobs yet"
            copy="Your generations will appear here."
          />
        )}
      </section>
      <aside className="job-detail">
        {current ? <JobDetail job={current} onError={onError} /> : null}
      </aside>
    </div>
  );
}

function JobDetail({ job }: { job: Job; onError: (s: string) => void }) {
  const stages = [
    "Prepare audio",
    "Separate / stems",
    "Convert voice",
    "Mix & master",
  ];
  return (
    <>
      <div className="job-title">
        <div>
          <Badge
            tone={
              job.status === "complete"
                ? "success"
                : job.status === "failed"
                  ? "danger"
                  : "neutral"
            }
          >
            {job.status}
          </Badge>
          <h2>
            {job.status === "complete"
              ? "Your audio is ready"
              : "Production in progress"}
          </h2>
          <p>{job.detail}</p>
        </div>
        <strong>{job.overall_percent}%</strong>
      </div>
      <div className="big-progress">
        <i style={{ width: `${job.overall_percent}%` }} />
      </div>
      <div className="stage-list">
        {stages.map((s, i) => (
          <div
            className={
              i < (job.completed_stages || 0)
                ? "done"
                : i === job.active_stage
                  ? "active"
                  : ""
            }
            key={s}
          >
            <span>{i < (job.completed_stages || 0) ? <Check /> : i + 1}</span>
            <div>
              <strong>{s}</strong>
              <small>
                {i === job.active_stage
                  ? `${job.stage_percent}/100`
                  : i < (job.completed_stages || 0)
                    ? "Complete"
                    : "Waiting"}
              </small>
            </div>
          </div>
        ))}
      </div>
      {job.status === "complete" && (
        <>
          <audio
            className="final-player"
            controls
            autoPlay
            src={`/api/jobs/${job.id}/audio`}
          />
          <a className="download" href={`/api/jobs/${job.id}/download`}>
            <Download />
            Download final WAV
          </a>
        </>
      )}
      {job.status === "failed" && <div className="error-box">{job.error}</div>}
      <details>
        <summary>Technical log</summary>
        <pre>{job.logs || "Waiting for model output…"}</pre>
      </details>
    </>
  );
}

function LibraryPage({ jobs }: { jobs: Job[] }) {
  return (
    <>
      <div className="page-intro">
        <div>
          <h2>Completed audio</h2>
          <p>Play or export anything generated on this Mac.</p>
        </div>
      </div>
      <div className="library-grid">
        {jobs.map((j) => (
          <article key={j.id}>
            <div className="cover">
              <AudioLines />
            </div>
            <div>
              <h3>
                {j.source_method === "Vocal only"
                  ? "Converted vocal"
                  : "My voice song"}
              </h3>
              <p>
                {j.quality_mode} · {new Date(j.created).toLocaleDateString()}
              </p>
            </div>
            <audio controls src={`/api/jobs/${j.id}/audio`} />
            <a href={`/api/jobs/${j.id}/download`}>
              <Download />
              Download WAV
            </a>
          </article>
        ))}
      </div>
      {!jobs.length && (
        <Empty
          icon={Library}
          title="Your library is empty"
          copy="Completed generations will be kept here."
        />
      )}
    </>
  );
}

function SettingsPage({ system }: { system: System | null }) {
  return (
    <>
      <div className="page-intro">
        <div>
          <h2>Studio settings</h2>
          <p>Local runtime and privacy configuration.</p>
        </div>
      </div>
      <div className="settings-grid">
        <section className="panel">
          <h3>Compute</h3>
          <div className="setting-row">
            <div>
              <strong>Processing device</strong>
              <span>Seed-VC and separation acceleration</span>
            </div>
            <Badge tone="success">{system?.device || "Checking"}</Badge>
          </div>
          <div className="setting-row">
            <div>
              <strong>Concurrent GPU jobs</strong>
              <span>Prevents unified-memory exhaustion</span>
            </div>
            <strong>1</strong>
          </div>
        </section>
        <section className="panel">
          <h3>Privacy</h3>
          <div className="setting-row">
            <div>
              <strong>Local-only mode</strong>
              <span>Audio never leaves this Mac</span>
            </div>
            <Badge tone="success">Enabled</Badge>
          </div>
          <div className="setting-row">
            <div>
              <strong>Server binding</strong>
              <span>Not exposed to the network</span>
            </div>
            <code>127.0.0.1</code>
          </div>
        </section>
      </div>
    </>
  );
}

export default App;
