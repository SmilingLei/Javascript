# AGENTS.md

## Cursor Cloud specific instructions

### What this repo contains
- `vue-hotel/` — the main product: "海棠春" hotel website. Vue 2 SPA frontend (webpack-dev-server, port 8080) + Express/MySQL backend in `vue-hotel/haitangchunserver/` (port 3000). Frontend proxies `/api/*` to the backend (`vue-hotel/config/index.js`).
- `lodash/` and `smilinglei-lodash.js` — a standalone hand-written lodash re-implementation exercise. Plain JS, no build/tests, nothing to run as a service.

### Services and how to run (dev)
| Service | Dir | Command | Port |
|---------|-----|---------|------|
| Backend API (Express) | `vue-hotel/haitangchunserver` | `npm start` (`nodemon index`) | 3000 |
| Frontend SPA (webpack 3) | `vue-hotel` | `NODE_OPTIONS=--openssl-legacy-provider npm run dev` | 8080 |
| Lint (frontend) | `vue-hotel` | `npm run lint` | — |
| Prod build (frontend) | `vue-hotel` | `NODE_OPTIONS=--openssl-legacy-provider npm run build` | — |

Standard setup/run commands live in `vue-hotel/README.md`.

### Non-obvious caveats
- **Node 22 + webpack 3**: the frontend uses webpack 3, which crashes on Node 17+ with an OpenSSL/md4 error. You MUST prefix frontend `dev`/`build` with `NODE_OPTIONS=--openssl-legacy-provider`. The backend needs no such flag.
- **MySQL is required and is NOT started automatically.** The backend connects on boot (`vue-hotel/haitangchunserver/db.js`: host `localhost`, user `root`, password `root`, db `test`, port 3306). MariaDB is used here. Start it with `sudo service mariadb start`. If the `test` database is empty/missing (no `.sql` schema/seed file ships in the repo), recreate it — schema is inferred from `haitangchunserver/api/api.js`:
  ```sql
  CREATE DATABASE IF NOT EXISTS test CHARACTER SET utf8mb4;
  USE test;
  CREATE TABLE IF NOT EXISTS users (user VARCHAR(50), password VARCHAR(100));
  CREATE TABLE IF NOT EXISTS room (id INT AUTO_INCREMENT PRIMARY KEY, `desc` VARCHAR(255));
  CREATE TABLE IF NOT EXISTS news (idnews INT AUTO_INCREMENT PRIMARY KEY, newstitle VARCHAR(255), date VARCHAR(50), content TEXT, author VARCHAR(100));
  CREATE TABLE IF NOT EXISTS guestbook (gbid INT AUTO_INCREMENT PRIMARY KEY, gbname VARCHAR(100), gbEmail VARCHAR(100), gbsub VARCHAR(255), gbcon TEXT);
  ```
  Root auth: this env sets `root`@`localhost` to `mysql_native_password` with password `root` so the node `mysql` driver can connect over TCP. Seed at least one `room` row (its `desc` column holds an image URL such as `http://127.0.0.1:3000/images/room1.jpg`) and one `users` row for the admin login flow.
- **Missing referenced files (added as stubs in this repo):** the app as originally committed did not compile — `vue-hotel/src/views/roomPic.vue` (imported by the router) and the entire `vue-hotel/static/` assets folder were absent, so webpack failed with "module not found" for `roomPic`, `static/images/steak.jpg`, and `static/images/haitangchun.png`. Minimal placeholder stubs were added so the frontend builds. Many other `static/images/*` assets are still absent and will 404 visually in the browser, but they do not break compilation (they are referenced from inline `style="background-image: url(...)"` strings, which webpack does not resolve). `index.html` also references a missing `ckeditor` script that 404s without affecting the main app.
- The contact/guestbook form (`vue-hotel/src/views/connect.vue`) and several admin views hard-code `http://127.0.0.1:3000` and `http://127.0.0.1:8080`, and backend CORS only allows `http://localhost:8080`. Use those exact hosts/ports.
