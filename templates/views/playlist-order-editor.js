export default function(component) {
  const root = component.parentElement;
  const data = component.data || {};
  const items = Array.isArray(data.items) ? data.items : [];
  const editable = Boolean(data.editable);
  const list = root.querySelector(".ezpo-list");
  const help = root.querySelector(".ezpo-help");

  const canonical = items.map(item => String(item.audio_hash || ""));
  let order = canonical.slice();

  try {
    const saved = JSON.parse(String(component.state?.order || ""));
    if (
      Array.isArray(saved) &&
      saved.length === canonical.length &&
      new Set(saved).size === canonical.length &&
      saved.every(value => canonical.includes(String(value)))
    ) {
      order = saved.map(String);
    }
  } catch (_) {}

  help.textContent = editable
    ? String(data.drag_label || "")
    : String(data.readonly_label || "");

  function emit() {
    component.setStateValue("order", JSON.stringify(order));
  }

  function itemByHash(hash) {
    return items.find(item => String(item.audio_hash || "") === String(hash));
  }

  function move(from, to) {
    if (!editable || from === to || from < 0 || to < 0) return;
    const next = order.slice();
    const [value] = next.splice(from, 1);
    next.splice(to, 0, value);
    order = next;
    emit();
    render();
  }

  function render() {
    list.replaceChildren();

    order.forEach((hash, index) => {
      const item = itemByHash(hash);
      if (!item) return;

      const row = document.createElement("div");
      row.className = "ezpo-item";
      row.draggable = editable;
      row.dataset.index = String(index);

      const pos = document.createElement("div");
      pos.className = "ezpo-pos";
      pos.textContent = String(index + 1);

      const handle = document.createElement("div");
      handle.className = "ezpo-handle";
      handle.textContent = "☰";

      const text = document.createElement("div");
      const title = document.createElement("div");
      title.className = "ezpo-title";
      title.textContent = String(item.title || "");
      const artist = document.createElement("div");
      artist.className = "ezpo-artist";
      artist.textContent = String(item.artist || "");
      text.append(title, artist);

      const buttons = document.createElement("div");
      buttons.className = "ezpo-buttons";

      const up = document.createElement("button");
      up.type = "button";
      up.textContent = "↑";
      up.disabled = !editable || index === 0;
      up.addEventListener("click", event => {
        event.preventDefault();
        move(index, index - 1);
      });

      const down = document.createElement("button");
      down.type = "button";
      down.textContent = "↓";
      down.disabled = !editable || index === order.length - 1;
      down.addEventListener("click", event => {
        event.preventDefault();
        move(index, index + 1);
      });

      buttons.append(up, down);
      row.append(pos, handle, text, buttons);

      if (editable) {
        row.addEventListener("dragstart", event => {
          row.classList.add("ezpo-dragging");
          event.dataTransfer.effectAllowed = "move";
          event.dataTransfer.setData("text/plain", String(index));
        });

        row.addEventListener("dragend", () => {
          row.classList.remove("ezpo-dragging");
          list.querySelectorAll(".ezpo-over").forEach(node => {
            node.classList.remove("ezpo-over");
          });
        });

        row.addEventListener("dragover", event => {
          event.preventDefault();
          row.classList.add("ezpo-over");
          event.dataTransfer.dropEffect = "move";
        });

        row.addEventListener("dragleave", () => {
          row.classList.remove("ezpo-over");
        });

        row.addEventListener("drop", event => {
          event.preventDefault();
          row.classList.remove("ezpo-over");
          const from = Number(event.dataTransfer.getData("text/plain"));
          const to = Number(row.dataset.index || index);
          if (Number.isInteger(from) && Number.isInteger(to)) {
            move(from, to);
          }
        });
      }

      list.appendChild(row);
    });
  }

  render();
}
