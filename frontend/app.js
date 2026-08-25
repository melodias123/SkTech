/* SK TECH — PUTER.JS AI BUILD
   AI stays in the browser through Puter.js.
   Retailers are optional and are handled by the backend.
   Amazon is never required for PC Builder to work.
*/
(() => {
  'use strict';

  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  let buildLinks = [];

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
    }[char]));
  }

  function safeUrl(value) {
    if (!value) return '';
    try {
      const url = new URL(String(value), window.location.origin);
      return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
    } catch {
      return '';
    }
  }

  function nav(id) {
    $$('.screen').forEach(screen => screen.classList.toggle('active', screen.id === id));
    $$('[data-screen]').forEach(button => button.classList.toggle('active', button.dataset.screen === id));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  document.addEventListener('click', event => {
    const button = event.target.closest('[data-screen]');
    if (button?.dataset.screen) nav(button.dataset.screen);
  });

  function addMessage(text, who = 'sk') {
    const chat = $('#messages');
    if (!chat) return null;
    const div = document.createElement('div');
    div.className = `msg ${who}`;
    const label = document.createElement('small');
    label.textContent = who === 'user' ? 'YOU' : 'SK · INTELLIGENCE';
    const body = document.createElement('p');
    body.textContent = text ?? '';
    div.append(label, body);
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
    return body;
  }

  async function waitForPuter(timeout = 10000) {
    const started = Date.now();
    while (!window.puter?.ai) {
      if (Date.now() - started > timeout) throw new Error('Puter AI has not loaded yet. Refresh the page and try again.');
      await new Promise(resolve => setTimeout(resolve, 150));
    }
    return window.puter;
  }

  async function puterAI(messages, options = {}) {
    await waitForPuter();
    const config = {
      model: 'gpt-5.6-luna',
      temperature: options.temperature ?? 0.2,
      max_tokens: options.maxTokens ?? 4500
    };

    try {
      const response = await window.puter.ai.chat(messages, { ...config, stream: true });
      let text = '';
      if (response && typeof response[Symbol.asyncIterator] === 'function') {
        for await (const part of response) {
          const chunk = part?.text ?? part?.message?.content ?? '';
          if (chunk) text += chunk;
          if (options.onChunk && chunk) options.onChunk(text);
        }
        if (text.trim()) return text.trim();
      }
    } catch (streamError) {
      // Fall through to a normal Puter response. This keeps the AI working if streaming is unavailable.
    }

    const response = await window.puter.ai.chat(messages, config);
    const text = response?.text ?? response?.message?.content ?? response?.content ?? '';
    if (!String(text).trim()) throw new Error('Puter AI returned an empty response.');
    return String(text).trim();
  }

  async function askSK(question) {
    const thinking = addMessage('Thinking…', 'sk');
    try {
      let liveContext = '';
      if (/price|buy|shop|ebay|amazon|rtx|radeon|ryzen|intel|gpu|cpu|ram|ssd/i.test(question)) {
        try {
          const response = await fetch(`/api/search?q=${encodeURIComponent(question)}&limit=5`, { headers: { Accept: 'application/json' } });
          if (response.ok) {
            const data = await response.json();
            const products = Array.isArray(data.products) ? data.products : [];
            if (products.length) {
              liveContext = '\n\nLIVE RETAIL CONTEXT:\n' + products.map(product =>
                `${product.retailer || product.source || 'Retailer'}: ${product.title || product.name || 'Product'} — ${product.price ?? 'N/A'} ${product.currency || ''} — ${product.url || ''}`
              ).join('\n');
            }
          }
        } catch {}
      }

      const answer = await puterAI([
        {
          role: 'system',
          content: 'You are SK, a premium PC and technology intelligence assistant. Give accurate, practical UK-focused advice. Never invent live prices, product availability or URLs. If live retailer context is supplied, use it carefully.'
        },
        { role: 'user', content: question + liveContext }
      ], {
        temperature: 0.2,
        maxTokens: 4500,
        onChunk: text => { if (thinking) thinking.textContent = text; }
      });

      if (thinking) thinking.textContent = answer;
    } catch (error) {
      if (thinking) thinking.textContent = `SK could not complete that request.\n\n${error.message}`;
    }
  }

  $('#ask')?.addEventListener('submit', async event => {
    event.preventDefault();
    const input = $('#askin');
    const question = input?.value.trim();
    if (!question) return;
    addMessage(question, 'user');
    input.value = '';
    await askSK(question);
  });

  $$('.quick').forEach(button => button.addEventListener('click', () => {
    const question = button.dataset.q;
    if (!question) return;
    nav('ask');
    addMessage(question, 'user');
    askSK(question);
  }));

  function componentLines(text) {
    const matches = [...String(text || '').matchAll(/(?:^|\n)\s*(CPU|GPU|Motherboard|RAM|Memory|Storage|SSD|PSU|Power Supply|Case|Cooler|Cooling)\s*[:\-]\s*(.+)/gi)];
    return matches.map(match => match[2].trim()).filter(Boolean);
  }

  function renderBuildLinks(container, links) {
    container.innerHTML = '';
    if (!links.length) {
      container.innerHTML = `<div class="affiliate-disclosure"><div class="affiliate-disclosure-title">RETAIL LINKS OPTIONAL</div><div class="affiliate-disclosure-text">Your AI build is complete. Live retailer links will appear when connected retailer feeds return matching products. Amazon is not required.</div></div>`;
      return;
    }

    const title = document.createElement('h3');
    title.textContent = 'BUY YOUR BUILD';
    container.appendChild(title);

    links.forEach(product => {
      const row = document.createElement('div');
      row.className = 'buy-link mini';
      const info = document.createElement('span');
      const price = product.price != null ? `${product.price} ${product.currency || 'GBP'}` : 'Price unavailable';
      info.textContent = `${product.component || 'Component'}: ${product.title || product.name || 'Product'} · ${product.retailer || product.source || 'Retailer'} · ${price}`;
      row.appendChild(info);
      const url = safeUrl(product.url || product.link);
      if (url) {
        const link = document.createElement('a');
        link.href = url;
        link.target = '_blank';
        link.rel = 'sponsored noopener noreferrer';
        link.textContent = 'BUY →';
        row.appendChild(link);
      }
      container.appendChild(row);
    });
  }

  async function findRetailProducts(component) {
    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(component)}&limit=2`, { headers: { Accept: 'application/json' } });
      if (!response.ok) return [];
      const data = await response.json();
      return (Array.isArray(data.products) ? data.products : [])
        .map(product => ({ ...product, component }))
        .filter(product => safeUrl(product.url));
    } catch {
      return [];
    }
  }

  $('#build')?.addEventListener('click', async () => {
    const briefInput = $('#brief');
    const button = $('#build');
    const output = $('#output');
    const status = $('#bst');
    const actions = $('#buildactions');
    const openAll = $('#openall');
    const brief = briefInput?.value.trim();

    if (!brief) {
      briefInput?.focus();
      return;
    }

    button.disabled = true;
    actions?.classList.add('hidden');
    if (openAll) openAll.classList.add('hidden');
    buildLinks = [];
    status.textContent = 'ENGINEERING';
    output.innerHTML = `<div class="empty"><div class="build-spinner">⌬</div><h3>Engineering your configuration…</h3><p>SK is using Puter AI to structure the build before checking connected retailer feeds.</p></div>`;

    try {
      const buildText = await puterAI([
        {
          role: 'system',
          content: `You are SK PC Build Engine. Design a complete, compatible UK PC from the user's brief. This is the AI decision layer. Return clear headings for CPU, GPU, Motherboard, RAM, Storage, PSU, Case and Cooling where appropriate. Include a total estimated component cost only if you can calculate it from stated values; otherwise say that live pricing is unavailable. Explain compatibility, expected performance, upgradeability and important trade-offs. Do not invent live retailer prices or URLs. Do not refuse simply because Amazon is not configured.`
        },
        { role: 'user', content: brief }
      ], {
        temperature: 0.15,
        maxTokens: 3500,
        onChunk: text => {
          output.innerHTML = `<div class="buildtext">${esc(text)}</div>`;
        }
      });

      output.innerHTML = `<div class="buildtext">${esc(buildText)}</div><div class="links" id="links"></div>`;
      const linksContainer = $('#links');
      const components = [...new Set(componentLines(buildText))].slice(0, 8);

      for (const component of components) {
        const products = await findRetailProducts(component);
        buildLinks.push(...products);
      }

      buildLinks = buildLinks.filter((item, index, array) => {
        const key = `${item.retailer || item.source}|${item.url}`;
        return array.findIndex(other => `${other.retailer || other.source}|${other.url}` === key) === index;
      });

      renderBuildLinks(linksContainer, buildLinks);
      status.textContent = buildLinks.length ? 'READY · RETAIL LINKS LIVE' : 'READY · RETAIL LINKS OPTIONAL';
      actions?.classList.remove('hidden');
      if (buildLinks.length) openAll?.classList.remove('hidden');
    } catch (error) {
      status.textContent = 'ERROR';
      output.innerHTML = `<div class="empty"><h3>SK could not complete the build.</h3><p>${esc(error.message)}</p></div>`;
    } finally {
      button.disabled = false;
    }
  });

  $('#openall')?.addEventListener('click', () => {
    if (!buildLinks.length) return;
    buildLinks.forEach((product, index) => {
      const url = safeUrl(product.url);
      if (url) setTimeout(() => window.open(url, '_blank', 'noopener,noreferrer'), index * 180);
    });
  });

  $('#shopform')?.addEventListener('submit', async event => {
    event.preventDefault();
    const query = $('#shopin')?.value.trim();
    const products = $('#products');
    const status = $('#retailstatus');
    if (!query) return;

    status.textContent = 'SEARCHING…';
    products.innerHTML = `<div class="empty shop-empty"><div class="build-spinner">◇</div><h3>Searching connected retailers…</h3><p>Checking eBay/EPN and any other configured retailer sources.</p></div>`;

    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=20`, { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error(`Retail search failed (${response.status}).`);
      const data = await response.json();
      const items = Array.isArray(data.products) ? data.products : [];

      if (!items.length) {
        status.textContent = 'NO RESULTS';
        products.innerHTML = `<div class="empty shop-empty"><h3>No live listings found.</h3><p>Try a broader search such as RTX 5080, Ryzen 7 or DDR5 32GB.</p></div>`;
        return;
      }

      status.textContent = 'LIVE';
      products.innerHTML = items.map(item => {
        const title = item.title || item.name || 'Hardware';
        const image = safeUrl(item.image || item.image_url || item.imageUrl);
        const url = safeUrl(item.url || item.link || item.buy_url || item.affiliate_url);
        const retailer = item.retailer || item.source || item.store || 'RETAILER';
        const price = item.price != null ? `${item.price} ${item.currency || 'GBP'}` : 'Price unavailable';
        return `<article class="product"><div class="product-media">${image ? `<img src="${esc(image)}" alt="${esc(title)}" loading="lazy">` : '<div class="product-no-image">NO IMAGE</div>'}</div><div class="product-body"><small>${esc(retailer)}</small><h3>${esc(title)}</h3><div class="price">${esc(price)}</div>${url ? `<a href="${esc(url)}" target="_blank" rel="sponsored noopener noreferrer">VIEW LISTING ↗</a>` : ''}</div></article>`;
      }).join('');
    } catch (error) {
      status.textContent = 'OFFLINE';
      products.innerHTML = `<div class="empty shop-empty"><h3>Retail search unavailable.</h3><p>${esc(error.message)}</p></div>`;
    }
  });

  $$('.labgrid button').forEach(button => button.addEventListener('click', () => {
    const topic = button.dataset.topic;
    if (!topic) return;
    nav('ask');
    const question = `Give me a detailed Hardware Lab lesson about ${topic}. Explain what it is, which specifications matter, how to compare products, common mistakes and what a PC builder should consider.`;
    addMessage(question, 'user');
    askSK(question);
  }));

  async function loadRetailerStatus() {
    const status = $('#retailstatus');
    if (!status) return;
    try {
      const response = await fetch('/api/retailers', { headers: { Accept: 'application/json' } });
      const data = await response.json();
      const ebay = data?.ebay || {};
      const amazon = data?.amazon || {};
      const ebayLive = ebay.configured || ebay.api_configured;
      const epn = ebay.epn_enabled || ebay.epn_configured;
      const amazonLive = amazon.configured;
      status.textContent = ebayLive ? `eBAY${epn ? ' · EPN' : ''}${amazonLive ? ' · AMAZON' : ''} LIVE` : 'RETAILERS READY';
    } catch {
      status.textContent = 'RETAIL STATUS UNAVAILABLE';
    }
  }

  async function loadYouTube() {
    const videos = $('#videos');
    if (!videos) return;
    try {
      const response = await fetch('/api/youtube', { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error('YouTube unavailable');
      const data = await response.json();
      const list = Array.isArray(data.videos) ? data.videos : [];
      if (!list.length) return;
      videos.innerHTML = list.map(video => {
        const image = safeUrl(video.thumbnail || video.image);
        const url = safeUrl(video.url);
        return `<article class="video">${image ? `<img src="${esc(image)}" alt="${esc(video.title || 'SK Builds video')}" loading="lazy">` : ''}<div><small>SK BUILDS</small><h3>${esc(video.title || 'SK Builds video')}</h3>${url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">WATCH ON YOUTUBE ↗</a>` : ''}</div></article>`;
      }).join('');
    } catch {
      // Keep the designed empty state. YouTube is optional.
    }
  }

  nav('home');
  loadRetailerStatus();
  loadYouTube();
})();
