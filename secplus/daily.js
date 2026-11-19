// "One thing a day": a fixed calendar of concepts, one per day, following the
// lesson order. Each day shows one animated lesson scene and quizzes 3 cards.
// Day 1 is START (US Eastern). The noon phone reminder uses this same calendar,
// so the app and the reminder always agree on today's concept.
(function (root) {
  'use strict';
  const START = '2026-11-19';
  // [lesson id, scene index, title, card terms to quiz]
  const PLAN = [
    ['cia', 0, 'The CIA triad', ['Encryption', 'Hashing', 'DDoS']],
    ['cia', 1, 'Confidentiality', ['Encryption', 'Encryption in Transit', 'Data Exfiltration']],
    ['cia', 2, 'Integrity', ['Hashing', 'SHA', 'HMAC']],
    ['cia', 3, 'Availability', ['DDoS', 'Single Point of Failure (SPOF)', 'Geographic Redundancy']],
    ['crypto', 0, 'Symmetric encryption', ['Symmetric Encryption', 'AES', 'Encryption at Rest']],
    ['crypto', 1, 'Public and private keys', ['Asymmetric Encryption', 'Public Key', 'Private Key', 'RSA']],
    ['crypto', 2, 'Hashing', ['Hashing', 'SHA', 'HMAC']],
    ['crypto', 3, 'Certificates and PKI', ['PKI', 'Certificate Authority (CA)', 'Registration Authority (RA)', 'Key Escrow']],
    ['network', 0, 'Network zones and the DMZ', ['Security Zoning', 'Proxy Server', 'Centralized Proxy']],
    ['network', 1, 'Firewall vs WAF', ['WAF', 'NGFW', 'Deep Packet Inspection (DPI)']],
    ['network', 2, 'IDS vs IPS', ['IDS', 'IPS', 'Event Monitoring']],
    ['network', 3, 'Jump servers', ['Jump Server', 'Least Privilege', 'Audit Trail']],
    ['network', 4, 'Honeypots', ['Honeypot', 'Honeynet', 'Honeyfile', 'Honeytoken']],
    ['web', 0, 'How a website works', ['Input Validation', 'Input Sanitization', 'WAF']],
    ['web', 1, 'SQL injection', ['SQL Injection', 'Input Validation', 'Input Sanitization']],
    ['web', 2, 'Cross-site scripting (XSS)', ['Cross-Site Scripting (XSS)', 'XSS', 'Session Hijacking']],
    ['web', 3, 'Directory traversal', ['Directory Traversal', 'Input Validation', 'Least Privilege']],
    ['web', 4, 'Buffer overflow', ['Buffer Overflow', 'Memory Injection', 'Integer Overflow']],
    ['passwords', 0, 'Brute force', ['Brute Force Attack', 'Credential Stuffing', 'Passkey']],
    ['passwords', 1, 'Password spraying', ['Brute Force Attack', 'Credential Stuffing', 'Authentication Logs']],
    ['passwords', 2, 'Credential stuffing', ['Credential Stuffing', 'Password Vault', 'Single Sign-On (SSO)']],
    ['passwords', 3, 'MFA', ['Passkey', 'Hardware Token', 'Single Sign-On (SSO)']],
    ['floods', 0, 'DDoS', ['DDoS', 'SYN Flood', 'Amplified DDoS']],
    ['floods', 1, 'Reflection and amplification', ['Reflected DDoS', 'Amplified DDoS', 'DDoS']],
    ['floods', 2, 'ARP spoofing', ['ARP Spoofing', 'DNS Poisoning', 'Session Hijacking']],
    ['floods', 3, 'DNS poisoning', ['DNS Poisoning', 'DNS Sinkholing', 'DNS Filtering']],
    ['access', 0, 'Role-based access (RBAC)', ['Role-Based Access Control (RBAC)', 'Least Privilege', 'Attribute-Based Access Control (ABAC)']],
    ['access', 1, 'Attribute-based access (ABAC)', ['Attribute-Based Access Control (ABAC)', 'Policy-driven Access Control', 'Time-of-Day Restrictions']],
    ['access', 2, 'MAC and DAC', ['Mandatory Access Control (MAC)', 'Discretionary Access Control (DAC)', 'Data Classification']],
    ['access', 3, 'Least privilege and just-in-time', ['Least Privilege', 'Just-in-Time Permissions', 'Ephemeral Credentials']],
    ['people', 0, 'Phishing', ['Phishing Campaign', 'Personnel Training', 'Spear Phishing']],
    ['people', 1, 'Spear phishing and whaling', ['Spear Phishing', 'Whaling', 'Phishing Campaign']],
    ['people', 2, 'Vishing', ['Vishing', 'Personnel Training', 'Whaling']],
    ['risk', 0, 'Single loss expectancy (SLE)', ['Single Loss Expectancy (SLE)', 'Exposure Factor (EF)', 'Annualized Loss Expectancy (ALE)']],
    ['risk', 1, 'Annualized loss expectancy (ALE)', ['Annualized Loss Expectancy (ALE)', 'Single Loss Expectancy (SLE)', 'Exposure Factor (EF)']],
    ['risk', 2, 'Four risk responses', ['Risk Transference', 'Risk Avoidance', 'Risk Acceptance', 'Risk Mitigation']],
    ['risk', 3, 'RPO and RTO', ['RPO', 'RTO', 'MTTR']],
  ].map(([lesson, scene, title, terms]) => ({ lesson, scene, title, terms }));

  // Day number for a local date: START is day 1.
  function dayNumber(date) {
    const [y, m, d] = START.split('-').map(Number);
    return Math.floor((Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) - Date.UTC(y, m - 1, d)) / 86400000) + 1;
  }
  // After the last day the plan starts over, so old concepts come back for review.
  function forDay(n) { const len = PLAN.length; return PLAN[(((Math.max(1, n) - 1) % len) + len) % len]; }

  const api = { START, PLAN, dayNumber, forDay };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SecDaily = api;
})(this);
