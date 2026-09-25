# Front-End Guide

> **Architecture Design Guide · Front-End**
> A short, cloud-agnostic guide to how we build and ship the browser side of an application. It applies whether the app runs on **Azure** or **AWS**. Where the two clouds differ, the difference is shown side by side.

---

## 1. Scope

**Covers:** the single-page application (SPA) the user sees, how it talks to the backend, how it is configured per environment, how it is hosted, how it authenticates, and how it is built and deployed.

**Does not cover:** the API layer, the AI service, the database, or infrastructure-as-code internals.

**Assumed shape of the system:**

```
Browser (SPA)  --HTTPS-->  Edge (CDN + WAF)  -->  Static hosting (the SPA files)
                                             \->  /api/*  -->  API service (private network)
```

The frontend is a set of static files served from a CDN. Everything dynamic comes from the API over `/api/*`. The frontend has no server of its own.

---

## 2. The rules (non-negotiable)

These hold on every cloud and every project.

1. **The frontend talks only to the API.** Never to a database, a queue, an AI provider, or a secret store. All authority lives server-side.
2. **Nothing in the bundle is secret.** Everything shipped to the browser is public. No API keys, no connection strings, no privileged tokens. Only public, environment-specific values may be baked into the build.
3. **Server data lives in the server-state library, not in hand-managed client state.** Let the cache library own freshness, refetching, and loading/error status.
4. **Change data, not the screen.** Update state and let the UI redraw. Never poke the DOM directly.
5. **Bound concurrency for batch work.** Never fire an unbounded burst of requests. Cap in-flight calls.
6. **Persist workflow state through the API.** A user must be able to close the tab and resume. State that matters is saved server-side, not trapped in the browser.
7. **Authentication is handled by the platform or edge, not by frontend code.** The SPA never sees a password and never stores a long-lived secret. The API receives a trusted identity from the hosting layer.
8. **Same-origin API calls.** In deployed environments the SPA calls `/api/...` on its own hostname and the hosting layer proxies to the API. No cross-origin calls from the browser in production.
9. **One build per environment, driven by config, not code edits.** dev, uat, and prod are built from the same source with different environment values.
10. **The frontend is deployed by a pipeline, never by hand.**
11. **Every kind of code has exactly one home.** The folder layout in section 4 is fixed. No new top-level folders, no dumping grounds, and import direction is enforced by lint. Code in the wrong place is a review blocker, not a style nit.

**How strictly to apply this.** The eleven rules above apply from the first commit, including on an MVP, because they are cheap to follow at the start and expensive to retrofit. Everything else in this guide is a default, not a mandate. An MVP can skip the quality bar in section 11 beyond typecheck, use the minimum form bar in section 5.9, and have no state store. What an MVP must not do is leave a secret in the build, call the API from more than one place, or put a screen somewhere other than `pages/`. When a rule and a project disagree, the project's decision log records why, and the disagreement is a review conversation rather than a failure.

---

## 3. Default stack

React with TypeScript is the default. Each tool answers exactly one question. If you are lost in the code, ask which question you are dealing with.

| Question | Default tool | Notes |
| --- | --- | --- |
| What should be on screen? | **React 18** | Components. UI is a function of state. |
| Are the data shapes right? | **TypeScript** | Strict mode on. Types for props and API payloads. |
| How does it become files? | **Vite** | Dev server with hot reload. Production bundler. Hashed asset filenames. |
| Which screen am I on? | **Wouter** | Tiny client-side router. A heavier router is acceptable if the app needs nested layouts or data loaders. |
| What is the app doing right now? | **Zustand** | Client state: wizard step, toggles, unsaved input. |
| What does the server know? | **TanStack Query** | Server state: fetching, caching, invalidation, polling. |
| How does it look? | **Tailwind CSS** + **shadcn/ui** (Radix) | Utility classes plus accessible components copied into the repo. |

These are defaults, not laws. Swapping one is fine if the replacement still answers only its one question and the reason is written down in the project's decision log.

### 3.1 Coming from backend .NET: the ideas before the tools

The examples throughout this guide use an internal order-management app: staff create draft orders, view saved orders, and generate packing slips. The API paths and data shapes are illustrative contracts, not references to a particular repository.

Imagine building a toy shop. The browser is the shop window and the API is the stockroom. The window shows what is available and lets someone ask for something; the stockroom keeps the official records.

| Concept | Simple analogy | What it means in this app |
| --- | --- | --- |
| React component | A LEGO piece you can reuse | A function that describes a piece of the screen, such as a order card or a button. Small components compose into pages. |
| Props | Instructions handed to a LEGO builder | Inputs passed from a parent component to a child. A `OrderCard` receives an order and a callback to invoke when clicked. Think method arguments, including a delegate for the callback. |
| State | The current score on a scoreboard | Values that can change, such as the selected tab. Updating React state asks React to render again; changing an ordinary variable does not. |
| JSX / TSX | A drawing plan with spaces for values | HTML-like syntax inside JavaScript / TypeScript. It describes UI; it is not a Razor page rendered on the server. |
| Hook | A reusable set of instructions for remembering or doing something | A function such as `useOrders` that connects a component to React state or other behaviour. Call hooks at the top level of a component or another hook, not inside conditions or loops. Reusing a hook does not, by itself, share its local state. |
| Provider | Plugging a whole room into one power supply | Makes a value or service available to components below it. A query provider supplies the query client. This resembles making a dependency available, but is not ASP.NET dependency injection. |
| Vite and the bundle | Packing the toy kit into a delivery box | Vite builds browser-ready JavaScript, CSS, and assets. Think of the build/publish step; the output runs in the user's browser. |
| Wouter | Signposts inside the shop | Maps a browser URL to a screen. Unlike an API route, it chooses a component rather than executing a server endpoint. |
| Tailwind and shadcn/ui | Paint supplies and ready-made furniture | Tailwind supplies styling classes; shadcn supplies component source files you own and maintain. |

The three names that need more explanation are **Zustand** (shared browser memory), **TanStack Query** (managing copies of server data), and **Zod** (checking actual values). Sections 5.2 and 5.9 explain them with examples.

### 3.2 UI component libraries: the standard

**Correcting a common mental model.** React is not a UI kit. It only renders. The buttons, dialogs, dropdowns, tables, and date pickers come from a separate **component library** that sits on top of React. "Templates downloaded from the web" usually means marketplace admin templates, which bundle a random component library, a theme, and dozens of unvetted packages in one zip. Those are exactly what this standard rules out.

**The default stack, explained with a toy castle.** Our standard is "shadcn/ui on Radix with Tailwind". That is three names in one phrase, so here is what each one is, using three boxes for building a toy castle.

- **Radix is the box of moving parts.** Hinges, latches, and springs. A drawbridge that actually goes up and down, a door that closes when you press the right button, a gate that only opens for the right key. The parts work perfectly, but they are plain grey plastic with no colour and no decoration. In the app, Radix gives you a dialog that traps focus, a menu that opens with the keyboard, a tooltip that screen readers can announce. It does not care what any of it looks like.
- **Tailwind is the box of paints and stickers.** Instead of mixing your own colours every time, you get small labelled stickers: "blue", "rounded corners", "big padding", "shadow". You put the stickers directly on each piece. In code that is class names such as `rounded-lg bg-blue-600 px-4` written right on the element.
- **shadcn/ui is a friend who already built the castle pieces for you.** They took the grey Radix parts, decorated them with Tailwind stickers, and then handed you the actual pieces to keep in your own toy box. Not a picture of them, not a rental. Yours. If you want the tower a different colour, you repaint your own piece. Nobody has to ask permission, and nothing arrives from outside later to change it.

So the phrase means: working parts from Radix, painted with Tailwind, assembled by shadcn, stored in your repo under `components/ui/` where you can see and change every one.

The trade, told the same way: because the pieces live in your toy box, when your friend improves a piece you do not get the new version automatically. You go and pick it up. That is the deal in exchange for owning the code.

An app with no component library is the child who built the castle from cardboard and glue. That is fine for a small castle, and the doors can work well. The problem shows up when the castle grows and every new door has to be invented again, and each one has to get focus, keyboard, and screen-reader behaviour right by hand.

Component libraries come in three shapes:

| Shape | What you get | Examples (backer) |
| --- | --- | --- |
| **Headless primitives** | Behaviour and accessibility only: focus, keyboard, screen reader. No look. You style them. | Radix UI (WorkOS), React Aria (Adobe), Base UI (MUI team), Headless UI (Tailwind Labs) |
| **Copy-in kit on primitives** | Styled components generated into your repo. You own the files. | shadcn/ui (Vercel-backed, built on Radix) |
| **Full styled system** | A complete, opinionated look. Install and use. Harder to restyle. | Fluent UI React v9 (Microsoft), MUI (MUI company, Material Design), Ant Design (Alibaba), react-bootstrap, Chakra, Mantine |

Large vendors also publish their own design systems (IBM Carbon, Shopify Polaris, GitHub Primer, Adobe Spectrum). Use those only when building inside that vendor's ecosystem.

**What "battle-tested" means for code that runs in the browser.** The risks, in order of how often they actually bite:

1. **Supply chain.** The real one. In 2025 two waves of npm compromises (the maintainer-phishing attack on widely used utility packages in September, and the self-propagating "Shai-Hulud" worm in September and again in November) reached applications through transitive dependencies, not through the UI library anyone chose. Every production package in the lockfile is an entry point. The controls are in section 10, and they matter more than the choice of library.
2. **Server-side React frameworks.** The 2025 Next.js middleware authorisation bypass and the December 2025 React Server Components remote-code-execution flaw were both server-side. Our SPA-on-CDN model runs no Node server that renders React, so that entire class does not apply. That is a security reason to keep the architecture in section 1, not just a hosting preference.
3. **Cross-site scripting inside components.** Rare in mainstream libraries. The risk is components that accept HTML strings: rich-text editors, markdown renderers with raw HTML enabled, chart tooltips. Prefer libraries that render text, and never enable raw HTML in a markdown renderer.
4. **Abandonment.** An unmaintained library means unpatched advisories and a forced migration later.
5. **Governance surprises.** A library that ships behaviour nobody asked for is a trust problem even when it is harmless. Ant Design's 2018 holiday "easter egg", which altered production interfaces without opt-in, is the standard example.

**The approved set.** One library per application. Never mix two component systems in one app.

| Role | Standard | When to use the alternative |
| --- | --- | --- |
| Component library, default | **shadcn/ui on Radix + Tailwind** | Default for every new app. Components are generated into `components/ui/`, so the code is in the repo, reviewable, and patchable without waiting for a release. Radix packages are small, focused, and widely deployed. |
| Component library, full styled system | **Fluent UI React v9** (Microsoft) or **MUI** | Fluent when the app must look like Microsoft 365 or is embedded in Teams or SharePoint. MUI when a team wants a complete styled system with commercial support and a data grid. Record the choice in the decision log. |
| Component library, accessibility-first headless | **React Aria** (Adobe) | When accessibility compliance is the top requirement and the team will style everything itself. |
| Icons | **lucide-react** | One icon set per app. |
| Markdown rendering | **react-markdown** with `remark-gfm` | Raw HTML stays off. No `rehype-raw`. |
| Charts | See the data-visualisation guidance | Recharts or a similarly maintained library; never one that takes HTML strings. |

**Not approved:** marketplace admin templates; Ant Design (governance history and a sprawling dependency tree); any library with a single maintainer, no organisation behind it, or no release in the last twelve months; any component that requires `dangerouslySetInnerHTML` to work; a second icon set; a second component system in the same app.

**Adding any new dependency** is a review item, not a free action. The reviewer checks: who maintains it and whether an organisation stands behind it, when it was last released, weekly downloads, known advisories, licence, whether it runs install scripts, and how many transitive packages it adds. A dependency that adds more than a handful of transitive packages needs a stated reason.

---

## 4. Where everything lives

Every frontend uses the same layout, and every folder owns exactly one concept. This is the main defence against slop. When each kind of code has one home, code in the wrong place is visible in a diff, a reviewer can ask "why is this here?", and a new joiner knows where to look and where to add. Code that could live anywhere ends up everywhere.

One repository per deployable unit. The frontend repo, annotated with the concept each folder is home to:

```
{app}-ui/                                   # the React SPA  ->  static hosting
├── client/
│   ├── src/
│   │   ├── main.tsx                        # mounts React; nothing else            [entry]
│   │   ├── App.tsx                         # route table + top-level providers      [routing]
│   │   ├── pages/                          # one entry per route; may be a folder  [screens]
│   │   │   └── order-details/         #   index.tsx + this screen's own parts [screen-local]
│   │   ├── components/                     # UI used on two or more screens        [shared components]
│   │   │   └── ui/                         # shadcn copies; edit deliberately      [design system]
│   │   ├── hooks/                          # reusable behaviour: queries, polling  [server state · behaviour]
│   │   ├── lib/                            # api client, store, pure helpers       [client state · API · utilities]
│   │   └── index.css                       # Tailwind entry; global styles only    [styling]
│   └── public/                             # copied as-is; hosting config lives here [hosting · auth]
├── shared/                                 # types that mirror the API contract    [contracts]
├── vite.config.ts                          # build + path aliases (@/, @shared/)   [build]
├── tailwind.config.ts                      # palette, spacing, scanned files       [styling]
└── package.json                            # dependencies + scripts                [build]
```

### 4.1 What belongs in each folder, and what does not

| Folder | Owns | Must not contain |
| --- | --- | --- |
| `pages/` | One entry per route. A page may be a single file or a folder (`pages/<route>/index.tsx`) holding the screen plus the sub-components and hooks used only by that screen. | Direct `fetch` calls (those go through `lib/api.ts`), and widgets used by other screens (those move to `components/`). If one file in the folder grows past a few hundred lines, split it inside the folder. |
| `components/` | UI used on two or more screens. Takes props, renders, raises events. | Whole screens, and anything used by only one page. A component that owns a route's data and layout is a page and belongs in `pages/`. |
| `components/ui/` | The shadcn primitives copied into the repo. | App-specific logic. Changes here are design-system changes and are reviewed as such. |
| `hooks/` | Every data hook: queries, mutations, job polling, streaming. One place to see everything the frontend asks the API for, even when a hook has a single caller. Plus behaviour hooks used by more than one screen. | JSX. UI-only hooks used by one screen (keep those in the page folder). |
| `lib/` | The single API client, the Zustand store if there is one, pure helpers (semaphore, formatters). | React components, JSX, hooks. A `lib/utils.ts` that grows without limit is a dumping ground; split it by concern. |
| `shared/` | Types and validation schemas that mirror the API contract. Validation schemas (Zod) are runtime code and that is expected; they let the browser and the API check the same rules. | UI code, Node-only code, and database table definitions. The frontend imports types with `import type` and imports a schema at runtime only when it deliberately validates with it, so ORM packages never reach the bundle. |
| `public/` | Files served verbatim, including the hosting config. | Anything that needs a build step. |

### 4.2 Import direction

Dependencies point one way. A layer may import from layers below it, never above.

```
pages  ->  components  ->  hooks  ->  lib  ->  shared
```

- `lib/` never imports from `hooks/` or `components/`.
- `hooks/` never imports from `pages/`.
- `components/` never imports from `pages/`.
- One page never imports from another page's folder. If two pages need the same thing, it moves to `components/` or `hooks/`.
- Nothing imports `main.tsx`.

Enforce this with the ESLint `no-restricted-imports` rule or `eslint-plugin-boundaries`, so a violation fails CI rather than waiting for a reviewer to notice.

### 4.3 The "where does this go?" test

Before creating a file, answer one question. If the answer is unclear, the design is unclear.

| I am writing... | It goes in |
| --- | --- |
| A screen with a URL | `pages/<route>/index.tsx` |
| A widget or UI-only hook used by only that screen | The same `pages/<route>/` folder |
| Something rendered on more than one screen | `components/` |
| Any query, mutation, polling, or streaming hook, whoever uses it | `hooks/` (the call itself goes through `lib/api.ts`) |
| State the whole app shares | `lib/` (the store) |
| A pure function with no React and no network | `lib/` |
| A type the API also returns | `shared/` |
| A style used everywhere | `tailwind.config.ts` or `index.css`, not a per-component override |

### 4.4 Signs of slop to reject in review

- A new top-level folder such as `helpers/`, `utils/`, `common/`, or `misc/`. The layout above already has a home for everything.
- A `fetch(...)` outside `lib/api.ts`.
- A whole screen sitting in `components/`. It belongs in `pages/`, so that `components/` stays a list of things that are safe to reuse.
- One file that holds a screen's data fetching, its state, and all of its JSX. Split it: the queries and mutations become a hook in `hooks/`, the sections become small components in the page folder, and one file composes them.
- The same helper copied into two files instead of moved to `lib/`.
- A file over roughly 300 lines, or a component with more than five or six props. Neither is a hard limit. Both are a prompt to ask whether two things are living in one place.
- Server data written into the Zustand store.
- Inline styles or arbitrary Tailwind values (`w-[137px]`) where a design token exists.
- A "temporary" `any` or `// @ts-ignore` without a linked ticket.

**On `shared/`.** The frontend and the API live in separate repos, so "shared" types are only shared if something keeps them in sync. Pick one mechanism and write it down: a published internal package, a git submodule, or a generated client from the API's OpenAPI spec. A folder that is copied by hand will drift.

### 4.5 Naming conventions

Use these conventions consistently. They are team defaults, not React requirements.

| Item | Convention | Examples |
| --- | --- | --- |
| React component files | PascalCase with `.tsx` | `OrderCard.tsx`, `OrderSummary.tsx` |
| Standalone page files | PascalCase with a `Page` suffix | `OrdersPage.tsx` |
| Folders | Lowercase kebab-case | `order-details/`, `create-order/` |
| Hooks | camelCase starting with `use`, with `.ts` | `useOrders.ts`, `useJobPolling.ts` |
| Utilities and other modules | camelCase with `.ts` | `formatDate.ts`, `queryClient.ts`, `orderUiStore.ts` |
| Contract and schema modules | camelCase with `.ts` | `order.ts`, `orderSchema.ts` |
| Tests | Match the source filename, adding `.test` before the extension | `OrderCard.test.tsx`, `formatDate.test.ts` |
| Static assets | Lowercase kebab-case | `company-logo.svg`, `empty-results.png` |

**Exceptions:**

- A page folder keeps its `index.tsx` entry point, as shown in section 4.1. Name the component inside descriptively, such as `OrderDetailsPage`.
- Keep generated shadcn filenames as supplied, such as `button.tsx` and `alert-dialog.tsx`.
- Keep tool-defined or established entry/configuration names, such as `main.tsx`, `vite.config.ts`, and `index.css`.

**Names inside files:**

- Components, types, and interfaces use PascalCase: `OrderCard`, `Order`, `OrderCardProps`.
- Functions and variables use camelCase: `formatDate`, `selectedOrderId`.
- Booleans use descriptive `is`, `has`, or `can` prefixes where appropriate: `isSaving`, `hasChanges`, `canSubmit`.
- A component file's name matches its primary component: `OrderCard.tsx` exports `OrderCard`. Page entry files and generated shadcn files follow the exceptions above.

**Case matters.** Imports must match filename casing exactly. Never create files whose names differ only by case. This prevents a build that works on Windows from failing on Linux.

---

## 5. Core patterns

### 5.1 One API client

All network calls go through a single helper. One place for the base URL, headers, JSON handling, and error mapping.

```ts
// lib/api.ts
const BASE = import.meta.env.VITE_API_BASE_URL ?? "";   // "" = same origin in deployed envs

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}/api${path}`, {
    ...init,                                            // spread first, so headers below win
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new ApiError(res.status, body.error ?? `Request failed: ${res.status}`);
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") return null as T;
  return res.json();
}

async function upload<T>(path: string, form: FormData): Promise<T> {
  // No Content-Type header: the browser must set the multipart boundary itself.
  const res = await fetch(`${BASE}/api${path}`, { method: "POST", body: form, credentials: "include" });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json();
}

export const api = {
  get:    <T>(p: string) => request<T>(p),
  post:   <T>(p: string, body?: unknown) => request<T>(p, { method: "POST",  body: body && JSON.stringify(body) }),
  patch:  <T>(p: string, body?: unknown) => request<T>(p, { method: "PATCH", body: body && JSON.stringify(body) }),
  delete: <T>(p: string) => request<T>(p, { method: "DELETE" }),
  upload,
};
```

Three details that are easy to get wrong: spread the caller's options before setting headers, or the caller's headers silently replace the JSON content type. Return null on a 204 or empty body instead of calling `res.json()`. Never set a content type on a `FormData` upload.

Prefer keeping calls relative everywhere and letting the Vite dev server proxy `/api` to the local API (`server.proxy` in `vite.config.ts`). Then the code path is identical locally and deployed, and `VITE_API_BASE_URL` is only needed for the rare case of pointing a local UI at a remote API.

There is exactly one module that calls `fetch`. Streaming readers and upload helpers live in that module or import from it. A second "api client" is a review blocker.

### 5.2 Client state vs server state

This is the distinction that prevents most frontend bugs. State has three owners, and the question is always "who else needs this?"

| | Local state | Shared client state | Server state |
| --- | --- | --- | --- |
| Who needs it | One component and its children | Two or more screens, or a component far from where it is set | Anything that reads the database |
| Examples | Open panel, hovered row, form field text, current tab | Selected order ID across screens, wizard progress, sidebar collapsed | Orders, shipment status, user profile |
| Source of truth | The component | The browser session | The server |
| Tool | `useState` / `useReducer`, or the URL for anything a user should be able to link to | Zustand | TanStack Query |
| Lifetime | While mounted | This session | Cached copy, refreshed by the library |

Start with local state. Promote to Zustand only when a second screen needs the value. A store is not required for every toggle or form, and an app with no cross-screen state needs no store at all. Never put server data in Zustand. Never put UI toggles in TanStack Query.

**Zustand: a whiteboard in the room.** One child writes "we are on step 2," and everyone in the room can see it. A Zustand store holds shared browser values; components subscribe to the values they need and update when those values change. A component's `useState` is its own sticky note instead. Neither is a database. The whiteboard belongs to this running browser app, not every user, and it does not automatically survive a refresh. For a .NET developer, think of an observable in-memory state object, not a server singleton or ASP.NET session.

**TanStack Query: a librarian who keeps your borrowed copy up to date.** The official order lives on the server. TanStack Query asks the API for a copy, caches it, and tracks whether the request is loading, succeeded, or failed. Your hook supplies the API call; the library manages its lifecycle. It is not an ORM and never connects to the database.

Four words explain most of its usage:

- **Query:** asking to read something, such as "get order 42."
- **Query key:** the label on that cached copy, such as `['orders', '42']`. Include inputs that distinguish one result from another.
- **Mutation:** asking to change something through the API, such as "update the delivery instructions for order 42." Here, mutation means a write operation, not changing a JavaScript object directly.
- **Invalidation:** marking a cached copy as out of date. After a successful update, invalidate the relevant order queries so they can fetch updated data. The library does not automatically know which reads a write affects.

**One screen, three owners.** On an order-details screen, the open help panel belongs in local state. A selected order ID needed across screens can live in Zustand or the URL. The saved order and its shipment status belong in TanStack Query. While editing, the form holds a draft; after saving through the API, refresh the relevant cached data. Do not copy the entire server result into Zustand just to display it.

### 5.3 Long-running jobs: poll

Generating packing slips for a large order or exporting thousands of orders can take seconds to minutes. The API returns a job ID immediately. The frontend polls until the job is complete.

**Like ordering pizza.** You place the order once and receive an order number. You then ask "is order 42 ready?" every few seconds. You do not order another pizza each time you check. The job ID is that order number. HTTP `202 Accepted` means the order was accepted, not that the work has finished.

```
POST /api/orders/:orderId/packing-slip  ->  202 { jobId }
GET  /api/jobs/packing-slip/:jobId      ->  { status: "pending" | "processing" | "complete" | "failed", result? }
                                      # check every 2 seconds
```

Implement polling once, as a hook in `hooks/`. Either a TanStack Query with `refetchInterval` that stops on a terminal status, or a dedicated polling hook that owns submit, retry, abort on unmount, and a maximum duration. Every screen uses that one hook. Back off the interval for long jobs. Polling endpoints must be excluded from strict rate limits on the API side.

**Example: generate a packing slip for an order.**

1. The user clicks Generate packing slip. The frontend submits `POST /api/orders/{orderId}/packing-slip` once.
2. The API returns a `jobId`. The hook checks `GET /api/jobs/packing-slip/{jobId}` every two seconds.
3. While the status is `pending` or `processing`, the screen shows progress and disables the Generate packing slip button.
4. On `complete`, refresh the order data to show its generated packing slip. On `failed`, show the error.

This example assumes an application-defined **`useJobPolling` hook** in `hooks/useJobPolling.ts`. It is not a built-in React or TanStack Query hook, and its implementation is not included here. Its contract is to submit once, poll `/api/jobs/{jobType}/{jobId}`, stop on a terminal status, and call `onSuccess` or `onError`. It exposes `run` and `isRunning` and must handle cleanup and a maximum wait. In the usage snippet below, `queryClient`, `setError`, and `orderId` come from the surrounding component.

```tsx
const { run, isRunning } = useJobPolling<{ packingSlipId: string }>({
  jobType: "packing-slip",
  onSuccess: () => {
    // The saved data changed; refresh the screen's cached copy.
    queryClient.invalidateQueries({
      queryKey: ["orders"],
    });
  },
  onError: (message) => setError(message),
});

async function handleGeneratePackingSlip() {
  setError(null);
  try {
    await run({
      createPath: `/orders/${orderId}/packing-slip`,
      body: {},
    });
  } catch {
    // onError above has already set the message for the screen.
  }
}
```

`run` submits the request and waits through the polling cycle. `isRunning` drives the button's disabled state and progress indicator. The component renders the error set by `setError`. The API client adds `/api`, so `createPath` leaves that prefix out. The query key must match the query used to load the screen's data.

For a .NET developer, `await run(...)` is like awaiting a `Task` that coordinates several short HTTP requests. It does not keep the original POST connection open or block the browser UI while waiting.

**Stopping polling is not cancelling the job.** Leaving the screen or aborting the hook stops the browser from checking. The server job can continue; cancelling that work requires a separate API operation. A polling timeout likewise means the browser stopped waiting, not that the server job necessarily failed.

An order ID identifies the business record; a job ID identifies one background task; a packing-slip ID identifies the generated document. Keep them distinct. The `['orders']` query prefix covers the list and detail keys such as `['orders', orderId]`, so invalidation can refresh both.

### 5.4 Batch operations: bound the concurrency

"Generate packing slips for all 50 orders" must not fire 50 requests at once. Use a semaphore (a few lines of code, or `p-limit`) and run at most N jobs in flight, typically 3 to 5. Each slot owns the full lifecycle: submit, poll, integrate the result, release.

### 5.5 Streaming output

For chat-style token-by-token output use Server-Sent Events (SSE). The frontend reads `response.body.getReader()`, parses `data:` lines, and drains a token queue on a short interval for smooth display.

Streaming has hosting implications. The whole path from browser to API must pass chunked responses without buffering. See section 8 for the per-cloud notes.

| Pattern | Use for |
| --- | --- |
| Polling | Discrete jobs that finish once (generate packing slips, export orders) |
| Streaming | Continuous output (chat) |

### 5.6 Routing

Client-side routing swaps components without a page reload. Two things every host must be told:

- **SPA fallback.** Any unknown path must serve `index.html` so deep links and refreshes work.
- **API pass-through.** `/api/*` must be proxied to the API, not served from the static bucket.

### 5.7 Session persistence

Workflow state that the user would hate to lose is saved to the API on every meaningful change. On load, the app fetches the last session and rehydrates the store. The browser is a cache of the session, not its home.

### 5.8 Loading, empty, and error states

Every screen that fetches data has three extra states: loading, empty, and error. Design them. Wrap route-level components in an error boundary so one broken panel does not blank the whole app.

### 5.9 Forms and saving

**Validation schemas: a checklist at the door.** A label on a box might say "three red balls," but someone still needs to open it and check. A TypeScript type is the label: it helps check your code before it runs, but does not inspect incoming JSON at runtime. A validation schema is the checklist: "product code must not be empty; quantity must be a positive whole number." **Zod** is a library that runs that checklist against actual values and reports what failed. This is closer to DataAnnotations or FluentValidation than to an EF database schema. Declaring a schema does nothing until code invokes it.

**React Hook Form: the person holding the clipboard.** It tracks field values, edits, errors, and submission state. A **Zod resolver** is the adapter that runs the checklist and gives its errors to the form library. A **dirty** field is one whose value differs from its starting value. The form library manages the form; it does not save to the API for you.

For example, a user enters a blank product code. Zod catches the failed rule, React Hook Form associates the error with the product-code field, and your component displays the message. Once the form is valid, a mutation sends it through the API client. The API still validates independently. If the API is .NET, agree on the same contract and rules; C# cannot directly execute a shared TypeScript Zod module.

Most screens end in a submit. The minimum bar for every one of them is small.

- **Block duplicate submissions.** The submit button is disabled while the mutation or job is pending, using the pending flag the library already gives you.
- **Say what happened.** The user can see that it is working, that it worked, or that it failed with the API's message. A toast is fine. On failure the user's input stays so they can retry.
- **Check the obvious before sending.** File type, file size, and required fields. The API still validates; the browser check is for the user, not for security.

That is enough for simple actions such as generating a packing slip or choosing an order status.

The rest applies only to real data-entry forms, meaning several typed fields, dynamic rows, or anything a user fills in for more than a minute:

- Errors shown next to the field that failed, not only in a toast.
- A shared validation schema (Zod), ideally the one the API validates with.
- React Hook Form with the Zod resolver, so field errors and dirty tracking are not hand-written each time.
- Auto-save through the API, or a warning before navigation discards unsaved work.

Do not add these to a screen that does not need them.

#### Worked example: validate a draft order, then submit it

A staff member creates a draft order for one product by entering its product code and quantity. This small example teaches validation and submission; a full order can also contain customer details and multiple line items. Saving a draft does not charge a customer or start fulfillment.

This teaching example assumes `react-hook-form`, `@hookform/resolvers`, `zod`, and `@tanstack/react-query` are installed, and the app already has a `QueryClientProvider`. It uses the `api` helper from section 5.1 and the `@/` and `@shared/` aliases from section 4. The illustrative contract is `POST /api/orders`, accepting `{ productCode, quantity }` and returning HTTP `201 Created` with `{ id, productCode, quantity, status: "draft" }`.

**1. Write the checklist: `shared/orderSchema.ts`.**

```ts
import { z } from "zod";

export const createOrderSchema = z.object({
  productCode: z.string().trim()
    .min(1, "Enter a product code.")
    .max(50, "Use no more than 50 characters."),
  quantity: z.number()
    .int("Enter a whole number.")
    .min(1, "Order at least one item.")
    .max(100, "Order no more than 100 items."),
});

export type CreateOrderInput = z.infer<typeof createOrderSchema>;
export type Order = CreateOrderInput & { id: string; status: "draft" };
```

`trim()` removes surrounding spaces, so a product code containing only spaces fails. `z.infer` derives the input type from the schema instead of writing the same shape twice. The schema checks actual values at runtime; the type helps while writing code. The example's limit of 100 is a business rule chosen for teaching. See the [Zod basics](https://zod.dev/basics).

**2. Put the API operation in a hook: `client/src/hooks/useCreateOrder.ts`.**

```ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CreateOrderInput, Order } from "@shared/orderSchema";

export function useCreateOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (values: CreateOrderInput) =>
      api.post<Order>("/orders", values),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });
}
```

The API helper adds `/api` and converts the object to JSON. This hook owns the write operation and its pending/error/success state. After success it marks the order list out of date; the list's query must use the matching `["orders"]` key. `void` means we intentionally do not wait for that background refresh here. These are [TanStack Query mutation patterns](https://tanstack.com/query/latest/docs/framework/react/guides/mutations).

**3. Connect the fields to the checklist and the hook: `client/src/pages/create-order/index.tsx`.**

```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { createOrderSchema } from "@shared/orderSchema";
import type { CreateOrderInput } from "@shared/orderSchema";
import { useCreateOrder } from "@/hooks/useCreateOrder";

export function CreateOrderPage() {
  const createOrder = useCreateOrder();
  const { register, handleSubmit, reset, formState: { errors } } =
    useForm<CreateOrderInput>({
      resolver: zodResolver(createOrderSchema),
      defaultValues: { productCode: "", quantity: 1 },
    });

  function onSubmit(values: CreateOrderInput) {
    if (createOrder.isPending) return;
    createOrder.mutate(values, {
      onSuccess: () => reset(), // Clear only after the API confirms success.
    });
  }

  return (
    <form noValidate onSubmit={handleSubmit(onSubmit)}>
      <fieldset disabled={createOrder.isPending}>
        <legend>Create draft order</legend>

        <label htmlFor="productCode">Product code</label>
        <input id="productCode" {...register("productCode")}
          aria-invalid={Boolean(errors.productCode)}
          aria-describedby={errors.productCode ? "product-error" : undefined} />
        {errors.productCode && (
          <p id="product-error" role="alert">{errors.productCode.message}</p>
        )}

        <label htmlFor="quantity">Quantity</label>
        <input id="quantity" type="number" min={1} max={100} step={1}
          {...register("quantity", { valueAsNumber: true })}
          aria-invalid={Boolean(errors.quantity)}
          aria-describedby={errors.quantity ? "quantity-error" : undefined} />
        {errors.quantity && (
          <p id="quantity-error" role="alert">{errors.quantity.message}</p>
        )}

        <button type="submit">
          {createOrder.isPending ? "Creating..." : "Create draft order"}
        </button>
      </fieldset>

      {createOrder.isError && (
        <p role="alert">Could not save the order. Your input is still here; try again.</p>
      )}
      {createOrder.isSuccess && <p role="status">Draft order created.</p>}
    </form>
  );
}
```

`register` connects each field to React Hook Form. Browser input values are normally strings; `valueAsNumber: true` converts the quantity to a number before Zod validates it. An empty quantity becomes an invalid numeric value and fails validation too.

`handleSubmit` prevents a normal browser form navigation, runs validation through the [Zod resolver](https://github.com/react-hook-form/resolvers#zod), and calls `onSubmit` only when valid. `noValidate` lets this example show its own messages rather than browser pop-ups. The disabled fieldset prevents edits and repeat clicks while pending. `mutate` starts the request and exposes failures through `isError`; this example does not need a `try/catch` around it.

**Follow one click:** form values → Zod validation → `onSubmit` → mutation hook → API client → `POST /api/orders`. For example, product code `MUG-001` and quantity `2` become `{ "productCode": "MUG-001", "quantity": 2 }`. Invalid values stop before the API call. A successful response clears the form and refreshes the list; a failed request keeps the input.

The API still validates independently, including whether the product exists. If it returns structured field errors, map those to the fields with React Hook Form's `setError`; the generic message above is the fallback for request failures. This is a normal save, so it returns the saved order directly. Generating its packing slip later uses the separate job-and-poll pattern in section 5.3.

**Try it:** submit a blank product code, then quantities of `0`, `1.5`, and `101`. Each should show a field error without sending a request. With valid values, check the POST JSON in the browser Network tab. Test a failed response: the fields should remain filled and become editable again.

---

## 6. Configuration and environments

Three environments, built from the same source: **dev**, **uat**, **prod**.

**Build-time configuration only.** Vite bakes `VITE_*` variables into the bundle at build time. That prefix is a guardrail. A variable without it is never exposed to the browser. Treat every `VITE_*` value as public.

Typical values:

| Variable | dev (local) | Deployed |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://localhost:5000` | empty (same origin) |
| `VITE_APP_ENV` | `local` | `dev` / `uat` / `prod` |
| `VITE_TELEMETRY_KEY` | empty | public instrumentation key or connection string |

Anything that is not public, such as a tenant ID that must be injected into a hosting config file, is written into the built output by the pipeline, not committed.

**Local development.** The frontend runs on the Vite dev server against a locally running API. The API injects a mock user when running locally, so the full sign-in flow is never needed on a laptop.

---

## 7. Authentication

**The pattern is the same on both clouds.** The hosting or edge layer performs the OpenID Connect (OIDC) login, sets a session, and forwards a trusted identity header to the API. The SPA:

- redirects to the platform login URL when it receives a 401,
- asks the API "who am I" to get the display name and roles,
- never handles a password, a client secret, or a refresh token.

The identity provider can be Microsoft Entra ID on either cloud. Entra ID is a standard OIDC provider, so AWS front doors can use it directly.

| | Azure | AWS |
| --- | --- | --- |
| Where login happens | Azure Static Web Apps built-in auth | Application Load Balancer `authenticate-oidc` action in front of the API, or Amazon Cognito Hosted UI |
| Identity provider | Entra ID | Entra ID via OIDC, or Cognito (which can federate to Entra ID) |
| Trusted header the API reads | `x-ms-client-principal` (base64 JSON: userId, userDetails, userRoles) | `x-amzn-oidc-data` (JWT signed by the ALB; verify with the ALB public key) plus `x-amzn-oidc-identity` |
| Login redirect for the SPA | `/.auth/login/aad` | The ALB redirects unauthenticated requests to the IdP automatically; for Cognito Hosted UI the SPA redirects to the Cognito domain |
| Logout | `/.auth/logout` | Clear the ALB session cookie and hit the IdP end-session URL |
| Config file | `staticwebapp.config.json` (`routes`, `allowedRoles`, `responseOverrides`) | ALB listener rules in Terraform; CloudFront behaviours |
| Direct-access guard | API returns 403 without the header | API returns 403 without a valid `x-amzn-oidc-data`; ALB security group only accepts CloudFront |

**If the platform cannot gate auth for you** (for example a pure S3 and CloudFront site with no ALB), the fallback is the SPA doing the OIDC Authorization Code flow with PKCE using a maintained library, sending the access token as a bearer header, and the API validating the JWT. This is acceptable but adds auth code to the frontend. Prefer the platform-gated pattern.

Minimal Azure config for reference:

```json
{
  "navigationFallback": { "rewrite": "/index.html", "exclude": ["/assets/*"] },
  "routes": [
    { "route": "/login", "allowedRoles": ["anonymous"] },
    { "route": "/*", "allowedRoles": ["authenticated"] }
  ],
  "responseOverrides": {
    "401": { "redirect": "/.auth/login/aad", "statusCode": 302 }
  },
  "globalHeaders": {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin"
  }
}
```

---

## 8. Hosting and delivery

The SPA is static files behind a CDN with a Web Application Firewall (WAF). The API sits behind the same hostname under `/api/*`.

| Concern | Azure | AWS |
| --- | --- | --- |
| Static hosting | Azure Static Web Apps (SWA) | S3 bucket (private, Origin Access Control) behind CloudFront, or Amplify Hosting |
| Edge, CDN, WAF | Azure Front Door + WAF policy (OWASP managed rules, prevention mode) | CloudFront + AWS WAF (AWS managed rule groups) |
| `/api/*` proxy to the API | SWA Backend Link to the Container App | CloudFront behaviour `/api/*` with the ALB as origin |
| SPA fallback | `navigationFallback` in `staticwebapp.config.json` | CloudFront custom error responses mapping 403 and 404 to `/index.html` with 200, or a CloudFront Function URI rewrite. Amplify: a rewrite rule for extensionless paths to `/index.html` |
| Security headers on the HTML | `globalHeaders` in SWA config | CloudFront Response Headers Policy |
| Origin lock-down | Custom domain via Front Door; do not advertise the `*.azurestaticapps.net` hostname; API validates `X-Azure-FDID` | S3 only readable by the CloudFront OAC; ALB security group allows only the CloudFront managed prefix list; optional secret header added by CloudFront and checked at the ALB |
| Custom domain and TLS | Front Door managed certificate | ACM certificate in us-east-1 attached to CloudFront |
| Streaming (SSE) | Works through SWA Backend Link and Front Door | Route via CloudFront to an ALB. Do not put SSE through API Gateway REST, which buffers. Disable response compression on the `/api/*` behaviour |

**Caching rules** are the same everywhere. Vite emits hashed filenames under `assets/`, so:

| Path | Cache-Control |
| --- | --- |
| `/index.html` | `no-cache` (always revalidate) |
| `/assets/*` | `public, max-age=31536000, immutable` |

Getting this wrong produces the classic "users see a white page after a deploy" bug, because an old `index.html` references assets that no longer exist.

---

## 9. Build and deploy

The pipeline for the frontend is short. It runs on every push to the `dev`, `uat`, and `main` branches, mapped to the matching environment.

```
1. npm ci
2. npm run lint && npm run typecheck && npm test
3. npm run build            # with VITE_* values for the target environment
4. inject non-committed values into the built output (tenant ID, etc.)
5. publish the build output
6. invalidate the CDN cache for index.html
```

| Step | Azure | AWS |
| --- | --- | --- |
| Pipeline auth | GitHub OIDC federated credential to Entra ID (`azure/login`), no stored secrets | GitHub OIDC to an IAM role (`aws-actions/configure-aws-credentials` with `role-to-assume`), no stored keys |
| Publish | `Azure/static-web-apps-deploy` action with the SWA deployment token from Terraform outputs | `aws s3 sync dist/ s3://bucket --delete` with per-path cache headers, or Amplify's own build |
| Cache invalidation | Handled by SWA on deploy | `aws cloudfront create-invalidation --paths "/index.html"` |
| Infra | Terraform: `azurerm_static_web_app`, Front Door, WAF policy | Terraform: `aws_s3_bucket`, `aws_cloudfront_distribution`, `aws_wafv2_web_acl`, ACM |

Terraform provisions the hosting. The pipeline only publishes files. The pipeline never creates cloud resources by hand.

---

## 10. Security checklist (frontend)

- [ ] No secrets in the repo, in `VITE_*` variables, or in the built bundle.
- [ ] All API calls same-origin under `/api/*` in deployed environments. CORS is not needed in production; if it is, the origin list is exact, never `*`.
- [ ] Auth is platform-gated. The SPA holds no credentials and no refresh logic.
- [ ] Unknown routes fall back to `index.html`. `/api/*` never falls back.
- [ ] Security headers set on the HTML response: `X-Content-Type-Options`, `X-Frame-Options` or `frame-ancestors`, `Referrer-Policy`, `Strict-Transport-Security`, and a Content Security Policy that at minimum restricts `script-src` to self.
- [ ] Origin locked down so the WAF cannot be bypassed by hitting the storage or app hostname directly.
- [ ] `index.html` is not cached long-term. Hashed assets are cached immutable.
- [ ] User-supplied content is rendered as text, never as HTML. If rich HTML is required, it is sanitised.
- [ ] Dependencies are scanned in CI and pinned by lockfile.
- [ ] Telemetry sends no personal data beyond what the privacy review approved.

**Supply-chain controls.** These address the risk that actually reached applications in 2025, and they apply to every frontend regardless of which UI library it uses.

- [ ] The lockfile is committed and CI installs with `npm ci`, never `npm install`.
- [ ] A release cooldown is enforced: no package version younger than seven days is installed. Dependabot and Renovate both support a cooldown setting. Both 2025 npm worms were detected and pulled within days, so a cooldown alone would have avoided them.
- [ ] Install scripts are disabled (`ignore-scripts=true` in `.npmrc`). Lifecycle scripts are how the worms executed. The few tools that need a post-install step, such as Playwright's browser download, are run as an explicit command.
- [ ] Packages come through an organisation registry proxy (Azure Artifacts, AWS CodeArtifact, or Artifactory) so a poisoned version can be blocked for every project at once.
- [ ] Dependency advisories fail the build at high severity (`npm audit`, Dependabot alerts, or a scanner such as Snyk or Socket).
- [ ] GitHub Actions are pinned to a commit SHA, not a floating tag. The pipeline's own dependencies are part of the supply chain.
- [ ] The production package count is tracked. A pull request that grows it needs a stated reason.
- [ ] The component library is from the approved set in section 3.2, and there is only one of them in the app.

---

## 11. Quality bar

| Check | Tool | Runs |
| --- | --- | --- |
| Types | `tsc --noEmit`, strict mode | every push |
| Lint and format | ESLint, Prettier | every push |
| Folder boundaries | ESLint import-boundary rules (section 4.2); fails on upward imports and on `fetch` outside `lib/api.ts` | every push |
| Unit and component tests | Vitest + Testing Library | every push |
| End-to-end smoke | Playwright against the dev environment | after deploy to dev |
| Bundle size | Vite build report; fail if the main chunk grows past an agreed budget | every push |
| Accessibility | Keyboard-only walk-through of each new screen; axe check in Playwright | per feature |

A screen is done when it has loading, empty, and error states, works with keyboard only, and its data-fetching hook has a test.

---

## 12. Azure to AWS at a glance

| Role | Azure | AWS |
| --- | --- | --- |
| Static hosting | Static Web Apps | S3 + CloudFront, or Amplify Hosting |
| Edge and WAF | Front Door + WAF | CloudFront + AWS WAF |
| API proxy | SWA Backend Link | CloudFront behaviour to ALB |
| Auth gate | SWA built-in auth | ALB OIDC action or Cognito |
| Identity provider | Entra ID | Entra ID via OIDC, or Cognito |
| Trusted identity header | `x-ms-client-principal` | `x-amzn-oidc-data` |
| Hosting config | `staticwebapp.config.json` | CloudFront config in Terraform, or Amplify rewrites |
| Pipeline identity | Federated credential | IAM role via OIDC |
| Frontend telemetry | Application Insights JS SDK | CloudWatch RUM |

The application code is identical on both. Only the hosting layer, the identity header the API decodes, and the pipeline publish step change.

---

## 13. New frontend checklist

1. Create `{app}-ui` from the layout in section 4. Add the import-boundary lint rules on day one, before any feature code.
2. Set up the one API client with `VITE_API_BASE_URL` defaulting to same-origin.
3. Add the Zustand store and the TanStack Query client. Keep them separate.
4. Add the route table with an SPA fallback and a 401 redirect to platform login.
5. Add the hosting config for the target cloud (section 8) including caching and security headers.
6. Add the job-polling hook and the concurrency limiter.
7. Add session save and rehydrate against the API.
8. Add loading, empty, and error states plus a route-level error boundary.
9. Wire the pipeline: lint, typecheck, test, build, publish, invalidate.
10. Run the security checklist in section 10 before the first uat deploy.

---

## 14. Glossary

| Term | Meaning |
| --- | --- |
| SPA | Single Page Application. Downloads once, then updates the screen itself and only fetches data. |
| Client state | Data that lives only in the browser for this session. |
| Server state | Data that lives in the database, fetched via the API and cached in the browser. |
| Polling | Repeatedly asking the API whether a job has finished. |
| SSE | Server-Sent Events. A kept-open HTTP response that pushes text as it is generated. |
| Semaphore | A small gate that limits how many operations run at once. |
| SPA fallback | Hosting rule that serves `index.html` for any unknown path. |
| OIDC | OpenID Connect. The standard login protocol used by Entra ID, Cognito, and the ALB. |
| WAF | Web Application Firewall. Blocks common attack patterns at the edge. |
| OAC | Origin Access Control. Lets CloudFront read a private S3 bucket. |
| Federated credential | Short-lived pipeline login via GitHub OIDC. Nothing stored, nothing to rotate. |
