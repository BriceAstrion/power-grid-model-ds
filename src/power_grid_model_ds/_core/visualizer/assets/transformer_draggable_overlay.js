
/* SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org> */
/*
 * SPDX-License-Identifier: MPL-2.0
 */

(function () {
  "use strict";
  const GRAPH_ID = "cytoscape-graph";
  const LOAD_PREFIX = "__visual_load__";
  const GENERATOR_PREFIX = "__visual_generator__";
  const GENERATOR_RADIUS = 34;
  const GENERATOR_STROKE = 8;
  const GENERATOR_COLOR = "#D0FFE5";
  const LOAD_COLOR = "#FFF8F0";
  const PREFIX = "__visual_transformer__";
  const RADIUS = 33;
  const OFFSET = 18;
  const STROKE = 10;
  const instances = new WeakSet();

  function locate() {
    const root = document.getElementById(GRAPH_ID);
    if (!root) return null;
    for (const element of [root, ...root.querySelectorAll("*")]) {
      const cy = element._cyreg && element._cyreg.cy;
      if (cy && typeof cy.on === "function" && !cy.destroyed()) return cy;
    }
    return null;
  }

  function unit(from, to) {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const length = Math.hypot(dx, dy);
    return length > 1e-9 ? { x: dx / length, y: dy / length } : null;
  }

  function add(point, direction, distance) {
    return { x: point.x + direction.x * distance, y: point.y + direction.y * distance };
  }

  function circleEndpoint(center, toward, radius) {
    const direction = unit(center, toward);
    return direction ? add(center, direction, radius) : center;
  }

  function nodeEndpoint(node, toward) {
    const center = node.position();
    const direction = unit(center, toward);
    if (!direction) return center;
    // Native Cytoscape nodes are generally elliptical; support diamond nodes
    // too, without extending a stroke into their filled interiors.
    const width = node.outerWidth() / 2;
    const height = node.outerHeight() / 2;
    const shape = node.style("shape");
    let distance;
    if (shape === "diamond") {
      distance = 1 / (Math.abs(direction.x) / width + Math.abs(direction.y) / height);
    } else if (shape === "rectangle" || shape === "round-rectangle") {
      distance = Math.min(
        Math.abs(direction.x) > 1e-9 ? width / Math.abs(direction.x) : Infinity,
        Math.abs(direction.y) > 1e-9 ? height / Math.abs(direction.y) : Infinity
      );
    } else {
      distance = 1 / Math.sqrt((direction.x / width) ** 2 + (direction.y / height) ** 2);
    }
    return add(center, direction, distance);
  }

  function install(cy) {
    if (instances.has(cy)) return;
    const container = cy.container();
    if (!container) return;
    instances.add(cy);
    if (getComputedStyle(container).position === "static") container.style.position = "relative";
    const canvas = document.createElement("canvas");
    canvas.setAttribute("aria-hidden", "true");
    canvas.style.cssText = "position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:10;";
    container.appendChild(canvas);
    const ctx = canvas.getContext("2d");
    if (!ctx) { canvas.remove(); return; }
    let queued = false;
    let frame = null;
    let disposed = false;

    function drawLoadSymbols(ctx) {
      cy.nodes('node[group = "load_symbol"]').forEach(function (symbol) {
        const loadId = String(symbol.data("component_id"));
        const connection = cy.getElementById(
          LOAD_PREFIX + loadId + "__connection"
        );

        if (connection.empty()) return;

        const source = connection.source();
        if (source.empty()) return;

        const center = symbol.position();
        const start = nodeEndpoint(source, center);

        const original = cy.getElementById(loadId);
        const classes = original.empty() ? "" : original.classes();
        const isOpen = classes.includes("open_loading_appliance");

        const direction = unit(start, center) || { x: 1, y: 0 };

        const arrowLength = 78;
        const arrowHeadLength = 23;
        const arrowHeadWidth = 18;

        const arrowStart = add(center, direction, -arrowLength / 2);
        const arrowTip = add(center, direction, arrowLength / 2);
        const arrowBase = add(arrowTip, direction, -arrowHeadLength);

        const perpendicular = {
          x: -direction.y,
          y: direction.x,
        };

        ctx.save();
        ctx.strokeStyle = LOAD_COLOR;
        ctx.fillStyle = LOAD_COLOR;
        ctx.lineWidth = 9;
        ctx.lineCap = "butt";
        ctx.lineJoin = "butt";

        // Draw the connection from the electrical node to the load.
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(arrowStart.x, arrowStart.y);

        if (isOpen) {
          ctx.setLineDash([10, 7]);
        }

        ctx.stroke();
        ctx.setLineDash([]);

        // Draw the arrow shaft through the open arrowhead.
        ctx.beginPath();
        ctx.moveTo(arrowStart.x, arrowStart.y);
        ctx.lineTo(arrowTip.x, arrowTip.y);
        ctx.stroke();

        // Draw an open V-shaped load arrowhead.
        ctx.beginPath();
        ctx.moveTo(
          arrowBase.x + perpendicular.x * arrowHeadWidth,
          arrowBase.y + perpendicular.y * arrowHeadWidth
        );
        ctx.lineTo(arrowTip.x, arrowTip.y);
        ctx.lineTo(
          arrowBase.x - perpendicular.x * arrowHeadWidth,
          arrowBase.y - perpendicular.y * arrowHeadWidth
        );
        ctx.stroke();

        if (symbol.selected()) {
          // A dark outer stroke separates the selection indicator
          // from the bright load symbol and nearby network elements.
          ctx.save();
          ctx.strokeStyle = "#202020";
          ctx.lineWidth = 20;
          ctx.globalCompositeOperation = "destination-over";

          ctx.beginPath();
          ctx.moveTo(arrowStart.x, arrowStart.y);
          ctx.lineTo(arrowTip.x, arrowTip.y);
          ctx.moveTo(
            arrowBase.x + perpendicular.x * arrowHeadWidth,
            arrowBase.y + perpendicular.y * arrowHeadWidth
          );
          ctx.lineTo(arrowTip.x, arrowTip.y);
          ctx.lineTo(
            arrowBase.x - perpendicular.x * arrowHeadWidth,
            arrowBase.y - perpendicular.y * arrowHeadWidth
          );
          ctx.stroke();
          ctx.restore();
        }

        ctx.restore();
      });
    }

    function drawGeneratorSymbols(ctx) {
      cy.nodes('node[group = "generator_symbol"]').forEach(function (symbol) {
        const generatorId = String(symbol.data("component_id"));
        const connection = cy.getElementById(
          GENERATOR_PREFIX + generatorId + "__connection"
        );

        if (connection.empty()) return;

        const source = connection.source();
        if (source.empty()) return;

        const center = symbol.position();
        const start = nodeEndpoint(source, center);
        const end = circleEndpoint(
          center,
          start,
          GENERATOR_RADIUS + GENERATOR_STROKE / 2
        );

        const original = cy.getElementById(generatorId);
        const classes = original.empty() ? "" : original.classes();
        const isOpen = classes.includes("open_generating_appliance");

        ctx.save();
        ctx.strokeStyle = GENERATOR_COLOR;
        ctx.fillStyle = GENERATOR_COLOR;
        ctx.lineWidth = GENERATOR_STROKE;
        ctx.lineCap = "butt";

        // Connect the electrical node to the generator boundary.
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);

        if (isOpen) {
          ctx.setLineDash([10, 7]);
        }

        ctx.stroke();
        ctx.setLineDash([]);

        // Draw the generator's circular outline.
        ctx.beginPath();
        ctx.arc(center.x, center.y, GENERATOR_RADIUS, 0, Math.PI * 2);
        ctx.stroke();

        // Draw the G label at the centre.
        ctx.font = "bold 38px Arial, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("G", center.x, center.y);

        if (symbol.selected()) {
          // Dashed outer ring makes selection distinguishable
          // without depending on a change of colour.
          ctx.save();
          ctx.strokeStyle = GENERATOR_COLOR;
          ctx.lineWidth = 4;
          ctx.setLineDash([9, 7]);
          ctx.beginPath();
          ctx.arc(
            center.x,
            center.y,
            GENERATOR_RADIUS + GENERATOR_STROKE + 10,
            0,
            Math.PI * 2
          );
          ctx.stroke();
          ctx.restore();
        }

        ctx.restore();
      });
    }

    function redraw() {
      queued = false;
      frame = null;
      if (disposed || cy.destroyed() || !canvas.isConnected) return;
      const width = container.clientWidth;
      const height = container.clientHeight;
      const dpr = window.devicePixelRatio || 1;
      if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
        canvas.width = Math.round(width * dpr);
        canvas.height = Math.round(height * dpr);
      }
      const zoom = cy.zoom();
      const pan = cy.pan();
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      ctx.save();
      ctx.translate(pan.x, pan.y);
      ctx.scale(zoom, zoom);

      cy.nodes('node[group = "transformer_symbol"]').forEach(function (symbol) {
        const transformerId = String(symbol.data("component_id"));
        const fromEdge = cy.getElementById(PREFIX + transformerId + "__from");
        const toEdge = cy.getElementById(PREFIX + transformerId + "__to");
        if (fromEdge.empty() || toEdge.empty()) return;
        const source = fromEdge.source();
        const target = toEdge.target();
        if (source.empty() || target.empty()) return;
        const a = source.position();
        const b = target.position();
        const midpoint = symbol.position();
        const axis = unit(a, b) || { x: 1, y: 0 };
        const leftCenter = add(midpoint, axis, -OFFSET);
        const rightCenter = add(midpoint, axis, OFFSET);
        const leftStart = nodeEndpoint(source, leftCenter);
        const rightEnd = nodeEndpoint(target, rightCenter);
        const leftFinish = circleEndpoint(leftCenter, leftStart, RADIUS + STROKE / 2);
        const rightStart = circleEndpoint(rightCenter, rightEnd, RADIUS + STROKE / 2);
        const selected = symbol.selected();
        const color = selected ? symbol.data("symbol_selected_color") : symbol.data("symbol_color");
        ctx.strokeStyle = color || "#398de0";
        ctx.lineWidth = STROKE;
        ctx.lineCap = "butt";
        const original = cy.getElementById(transformerId);
        const classes = original.empty() ? "" : original.classes();
        if (classes.includes("open_branch")) ctx.setLineDash([12, 8]);

        // Trim each segment against the union of the two winding discs.
        // Unlike a canvas clip, this also prevents a connection from entering
        // the opposite winding when the symbol is dragged off the edge axis.
        // The outermost intersection is selected from the endpoint toward
        // the symbol; no connection stroke is drawn inside either circle.
        function outerBoundary(from, toward, centers) {
          const direction = unit(from, toward);
          if (!direction) return from;
          const radius = RADIUS + STROKE / 2;
          const distanceToTarget = Math.hypot(toward.x - from.x, toward.y - from.y);
          let firstEntry = Infinity;
          for (const center of centers) {
            const fx = from.x - center.x;
            const fy = from.y - center.y;
            const projection = fx * direction.x + fy * direction.y;
            const discriminant = projection * projection - (fx * fx + fy * fy - radius * radius);
            if (discriminant < 0) continue;
            const entry = -projection - Math.sqrt(discriminant);
            const exit = -projection + Math.sqrt(discriminant);
            if (exit >= 0 && entry <= distanceToTarget) {
              firstEntry = Math.min(firstEntry, Math.max(0, entry));
            }
          }
          return Number.isFinite(firstEntry) ? add(from, direction, firstEntry) : toward;
        }

        const circles = [leftCenter, rightCenter];
        const leftBoundary = outerBoundary(leftStart, leftCenter, circles);
        const rightBoundary = outerBoundary(rightEnd, rightCenter, circles);
        // Open-terminal markers cover the node-side end of the connection.
        // Start the stroke beyond the marker's far tip so no blue/yellow
        // segment protrudes through the hollow diamond.
        const markerLength = 2 * 15 + 2 / 2;
        function connectionStart(point, boundary, isOpen) {
          if (!isOpen) return point;
          const direction = unit(point, boundary);
          if (!direction) return point;
          const length = Math.hypot(boundary.x - point.x, boundary.y - point.y);
          return add(point, direction, Math.min(markerLength, length));
        }
        const fromStart = connectionStart(leftStart, leftBoundary, classes.includes("open_branch_from"));
        const toStart = connectionStart(rightEnd, rightBoundary, classes.includes("open_branch_to"));
        ctx.beginPath();
        ctx.moveTo(fromStart.x, fromStart.y);
        ctx.lineTo(leftBoundary.x, leftBoundary.y);
        ctx.moveTo(toStart.x, toStart.y);
        ctx.lineTo(rightBoundary.x, rightBoundary.y);
        ctx.stroke();
        ctx.setLineDash([]);

        function diamond(point) {
          const toward = unit(point, midpoint) || { x: 1, y: 0 };
          const side = { x: -toward.y, y: toward.x };
          const r = 15;
          // Use a thin grey outline for the terminal marker, independent of
          // the much thicker transformer connection stroke.
          ctx.save();
          ctx.strokeStyle = "#b7b7b7";
          ctx.lineWidth = 2;
          // Place the near tip at the node border, accounting for its outline.
          const center = add(point, toward, r + ctx.lineWidth / 2);
          ctx.beginPath();
          ctx.moveTo(center.x - toward.x * r, center.y - toward.y * r);
          ctx.lineTo(center.x + side.x * r * 0.85, center.y + side.y * r * 0.85);
          ctx.lineTo(center.x + toward.x * r, center.y + toward.y * r);
          ctx.lineTo(center.x - side.x * r * 0.85, center.y - side.y * r * 0.85);
          ctx.closePath();
          ctx.fillStyle = getComputedStyle(container).backgroundColor || "#555";
          ctx.fill();
          ctx.stroke();
          ctx.restore();
        }
        if (classes.includes("open_branch_from")) diamond(leftStart);
        if (classes.includes("open_branch_to")) diamond(rightEnd);
        // Separate paths: a second arc in the same path implicitly connects
        // the two arc starting points with a straight line.
        ctx.beginPath();
        ctx.arc(leftCenter.x, leftCenter.y, RADIUS, 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(rightCenter.x, rightCenter.y, RADIUS, 0, Math.PI * 2);
        ctx.stroke();
      });
      drawLoadSymbols(ctx);
      drawGeneratorSymbols(ctx);
      ctx.restore();
    }

    function schedule() {
      if (queued || disposed) return;
      queued = true;
      frame = requestAnimationFrame(redraw);
    }
    cy.on("render pan zoom position data style select unselect add remove layoutstop", schedule);
    const resize = new ResizeObserver(schedule);
    resize.observe(container);
    cy.one("destroy", function () {
      disposed = true;
      if (frame !== null) cancelAnimationFrame(frame);
      cy.off("render pan zoom position data style select unselect add remove layoutstop", schedule);
      resize.disconnect();
      canvas.remove();
    });
    schedule();
  }

  function discover() {
    const cy = locate();
    if (cy) install(cy);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", discover, { once: true });
  } else discover();
  // Dash may mount the graph wrapper before Cytoscape initializes. Observe
  // graph subtree additions as well as replacement of the wrapper itself.
  let discoveryQueued = false;
  const observer = new MutationObserver(function (mutations) {
    const root = document.getElementById(GRAPH_ID);
    const relevant = mutations.some(function (mutation) {
      if (root && root.contains(mutation.target)) return true;
      return Array.from(mutation.addedNodes).some(function (node) {
        return node.nodeType === 1 && (node.id === GRAPH_ID || (node.querySelector && node.querySelector("#" + GRAPH_ID)));
      });
    });
    if (!relevant || discoveryQueued) return;
    discoveryQueued = true;
    requestAnimationFrame(function () { discoveryQueued = false; discover(); });
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
