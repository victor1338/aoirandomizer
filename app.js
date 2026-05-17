const statusEl = document.getElementById("status");
const boardImageEl = document.getElementById("boardImage");
const groupsEl = document.getElementById("groups");
const randomizeButton = document.getElementById("randomizeButton");
const playerCountEl = document.getElementById("playerCount");

const TOP_AFAV_COUNT = 10;
const BOTTOM_FAV_COUNT = 12;
const AFAV_Y_OFFSET = 90;
const AFAV_MIDDLE_ROW_EXTRA_OFFSET = 50;
const FAV_X_OFFSET = 300;
const FAV_Y_OFFSET = 148;
const FAV_SLOT_W = 320;
const FAV_SLOT_H = 280;

const RAW_TOP_SLOTS = [
  [492, 160, 1132, 561],
  [2147, 160, 2787, 561],
  [99, 957, 739, 1358],
  [906, 957, 1546, 1358],
  [1731, 957, 2371, 1358],
  [2539, 957, 3179, 1358],
  [99, 1629, 739, 2030],
  [906, 1629, 1546, 2030],
  [1731, 1629, 2371, 2030],
  [2539, 1629, 3179, 2030],
];

function buildGridSlots({ left, top, cols, rows, cellW, cellH, gapX, gapY }) {
  const slots = [];
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const x1 = left + col * (cellW + gapX);
      const y1 = top + row * (cellH + gapY);
      slots.push([x1, y1, x1 + cellW, y1 + cellH]);
    }
  }
  return slots;
}

function pickCards(paths, count) {
  if (!paths.length || count <= 0) {
    return [];
  }
  const pool = [...paths];
  const picked = [];
  if (pool.length >= count) {
    for (let i = 0; i < count; i += 1) {
      const idx = Math.floor(Math.random() * pool.length);
      picked.push(pool.splice(idx, 1)[0]);
    }
    return picked;
  }
  for (let i = 0; i < count; i += 1) {
    picked.push(paths[Math.floor(Math.random() * paths.length)]);
  }
  return picked;
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Failed to load ${src}`));
    image.src = src;
  });
}

function drawImageFit(ctx, image, slot) {
  const [x1, y1, x2, y2] = slot;
  const targetW = x2 - x1;
  const targetH = y2 - y1;

  const targetRatio = targetW / targetH;
  const sourceRatio = image.width / image.height;

  let sx = 0;
  let sy = 0;
  let sw = image.width;
  let sh = image.height;

  if (sourceRatio > targetRatio) {
    sw = image.height * targetRatio;
    sx = (image.width - sw) / 2;
  } else {
    sh = image.width / targetRatio;
    sy = (image.height - sh) / 2;
  }

  ctx.drawImage(image, sx, sy, sw, sh, x1, y1, targetW, targetH);
}

function countsForPlayers(playerCount) {
  return {
    bookAction: 3,
    fraction: playerCount + 1,
    SH: playerCount + 1,
    spawn: 6,
    bon: playerCount + 3,
  };
}

function renderGroups(picked, counts) {
  groupsEl.innerHTML = "";

  Object.keys(picked).forEach((category) => {
    const cards = picked[category];
    const group = document.createElement("article");
    group.className = "group";

    const head = document.createElement("div");
    head.className = "group-head";

    const title = document.createElement("h3");
    title.textContent = category;

    const countEl = document.createElement("span");
    countEl.textContent = `${counts[category]} cards`;

    head.appendChild(title);
    head.appendChild(countEl);
    group.appendChild(head);

    const grid = document.createElement("div");
    grid.className = "card-grid";

    cards.forEach((path) => {
      const image = document.createElement("img");
      image.src = path;
      image.alt = `${category} card`;
      grid.appendChild(image);
    });

    group.appendChild(grid);
    groupsEl.appendChild(group);
  });
}

async function generateBoard(manifest) {
  const board = await loadImage(manifest.base_board);
  const afav = pickCards(manifest.categories.afav || [], TOP_AFAV_COUNT);
  const fav = pickCards(manifest.categories.fav || [], BOTTOM_FAV_COUNT);

  const topSlots = RAW_TOP_SLOTS.map((slot, index) => {
    let offset = AFAV_Y_OFFSET;
    if (index >= 2 && index <= 5) {
      offset += AFAV_MIDDLE_ROW_EXTRA_OFFSET;
    }
    return [slot[0], slot[1] + offset, slot[2], slot[3] + offset];
  });

  const lowerCards = buildGridSlots({
    left: 17,
    top: 2450,
    cols: 4,
    rows: 3,
    cellW: 748,
    cellH: 500,
    gapX: 64,
    gapY: 0,
  });

  const bottomSlots = lowerCards.map(([x1, y1]) => [
    x1 + FAV_X_OFFSET,
    y1 + FAV_Y_OFFSET,
    x1 + FAV_X_OFFSET + FAV_SLOT_W,
    y1 + FAV_Y_OFFSET + FAV_SLOT_H,
  ]);

  const canvas = document.createElement("canvas");
  canvas.width = board.width;
  canvas.height = board.height;
  const ctx = canvas.getContext("2d");

  ctx.drawImage(board, 0, 0);

  const afavImages = await Promise.all(afav.map((path) => loadImage(path)));
  afavImages.forEach((img, idx) => drawImageFit(ctx, img, topSlots[idx]));

  const favImages = await Promise.all(fav.map((path) => loadImage(path)));
  favImages.forEach((img, idx) => drawImageFit(ctx, img, bottomSlots[idx]));

  boardImageEl.src = canvas.toDataURL("image/jpeg", 0.92);
}

async function randomizeAll() {
  try {
    statusEl.textContent = "Randomizing...";
    const response = await fetch("asset_manifest.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Cannot load asset manifest.");
    }

    const manifest = await response.json();
    await generateBoard(manifest);

    const playerCount = Number(playerCountEl.value || 2);
    const counts = countsForPlayers(playerCount);
    const picked = {};

    Object.entries(counts).forEach(([category, count]) => {
      picked[category] = pickCards(manifest.categories[category] || [], count);
    });

    renderGroups(picked, counts);
    statusEl.textContent = "Setup generated.";
  } catch (error) {
    statusEl.textContent = error.message;
  }
}

randomizeButton.addEventListener("click", randomizeAll);
window.addEventListener("DOMContentLoaded", randomizeAll);
