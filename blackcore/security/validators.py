"""Security validators for input validation and SSRF prevention."""

import re
import socket
import ipaddress
import os
from urllib.parse import urlparse
from typing import List, Optional
import dns.resolver


class URLValidator:
    """Validates URLs to prevent SSRF and other security issues."""
    
    # Allowed URL schemes
    ALLOWED_SCHEMES = ['https']
    
    # Blocked IP ranges (private networks, loopback, etc.)
    BLOCKED_NETWORKS = [
        ipaddress.ip_network('0.0.0.0/8'),        # Current network
        ipaddress.ip_network('10.0.0.0/8'),       # Private network
        ipaddress.ip_network('100.64.0.0/10'),    # Shared address space
        ipaddress.ip_network('127.0.0.0/8'),      # Loopback
        ipaddress.ip_network('169.254.0.0/16'),   # Link-local
        ipaddress.ip_network('172.16.0.0/12'),    # Private network
        ipaddress.ip_network('192.0.0.0/24'),     # IETF protocol assignments
        ipaddress.ip_network('192.168.0.0/16'),   # Private network
        ipaddress.ip_network('224.0.0.0/4'),      # Multicast
        ipaddress.ip_network('240.0.0.0/4'),      # Reserved
        ipaddress.ip_network('255.255.255.255/32'), # Broadcast
        # IPv6
        ipaddress.ip_network('::1/128'),          # Loopback
        ipaddress.ip_network('fc00::/7'),         # Unique local
        ipaddress.ip_network('fe80::/10'),        # Link-local
        ipaddress.ip_network('ff00::/8'),         # Multicast
    ]
    
    # Cloud metadata endpoints to block
    BLOCKED_HOSTS = [
        '169.254.169.254',  # AWS/GCP metadata
        'metadata.google.internal',  # GCP metadata
        'metadata.azure.com',  # Azure metadata
    ]
    
    # Allowed domains (if allowlist mode is enabled)
    ALLOWED_DOMAINS: Optional[List[str]] = None
    
    def __init__(self, allowed_domains: Optional[List[str]] = None):
        """Initialize URL validator.
        
        Args:
            allowed_domains: Optional list of allowed domains (allowlist mode)
        """
        self.allowed_domains = allowed_domains
    
    def validate_url(self, url: str) -> bool:
        """Validate a URL for security issues.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is safe
            
        Raises:
            ValueError: If URL is unsafe with detailed reason
        """
        if not url:
            raise ValueError("URL cannot be empty")
        
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")
        
        # Check scheme
        if parsed.scheme not in self.ALLOWED_SCHEMES:
            raise ValueError(
                f"Only HTTPS URLs are allowed, got: {parsed.scheme}://"
            )
        
        # Check for empty hostname
        if not parsed.hostname:
            raise ValueError("URL must have a hostname")
        
        # Check blocked hostnames
        if parsed.hostname.lower() in [h.lower() for h in self.BLOCKED_HOSTS]:
            raise ValueError(f"Access to {parsed.hostname} is blocked")
        
        # Check allowed domains if in allowlist mode
        if self.allowed_domains:
            if not any(
                parsed.hostname.endswith(domain) 
                for domain in self.allowed_domains
            ):
                raise ValueError(
                    f"Domain {parsed.hostname} not in allowed list"
                )
        
        # Resolve hostname to IP and check
        try:
            # Get all IPs for the hostname
            ips = self._resolve_hostname(parsed.hostname)
            
            for ip_str in ips:
                try:
                    ip = ipaddress.ip_address(ip_str)
                except ValueError:
                    # Not a valid IP, skip
                    continue
                
                # Check against blocked networks
                for network in self.BLOCKED_NETWORKS:
                    if ip in network:
                        raise ValueError(
                            f"URL resolves to blocked network {network}: {ip}"
                        )
                    
        except socket.gaierror as e:
            raise ValueError(f"Cannot resolve hostname {parsed.hostname}: {e}")
        
        # Additional security checks
        self._check_url_length(url)
        self._check_suspicious_patterns(url)
        
        return True
    
    def _resolve_hostname(self, hostname: str) -> List[str]:
        """Resolve hostname to all IP addresses."""
        ips = []
        
        # Check if hostname is already an IP address
        try:
            ipaddress.ip_address(hostname)
            return [hostname]
        except ValueError:
            # Not an IP address, continue with DNS resolution
            pass
        
        try:
            # Try DNS resolution first
            resolver = dns.resolver.Resolver()
            resolver.timeout = 5.0
            resolver.lifetime = 5.0
            
            # Try A records (IPv4)
            try:
                answers = resolver.resolve(hostname, 'A')
                ips.extend(str(rdata) for rdata in answers)
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                pass
            
            # Try AAAA records (IPv6)
            try:
                answers = resolver.resolve(hostname, 'AAAA')
                ips.extend(str(rdata) for rdata in answers)
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                pass
                
        except Exception:
            # Fallback to socket resolution
            try:
                addr_info = socket.getaddrinfo(hostname, None)
                ips = list(set(addr[4][0] for addr in addr_info))
            except socket.gaierror:
                pass
        
        if not ips:
            # Try direct socket resolution as last resort
            try:
                ip = socket.gethostbyname(hostname)
                ips = [ip]
            except socket.gaierror:
                pass
        
        return ips
    
    def _check_url_length(self, url: str) -> None:
        """Check URL length limits."""
        if len(url) > 2048:  # Common browser limit
            raise ValueError("URL too long (max 2048 characters)")
    
    def _check_suspicious_patterns(self, url: str) -> None:
        """Check for suspicious patterns in URL."""
        suspicious_patterns = [
            r'@',  # Username in URL (potential phishing)
            r'\.\.',  # Directory traversal
            r'%00',  # Null byte
            r'%0[dD]%0[aA]',  # CRLF injection
            r'<script',  # XSS attempt
            r'javascript:',  # JS protocol
            r'data:',  # Data protocol
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                raise ValueError(f"Suspicious pattern detected in URL: {pattern}")


# Email validation regex (RFC 5322 simplified)
EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}'
    r'[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
)

# URL validation regex (simplified)
URL_REGEX = re.compile(
    r'^https://'  # Must be HTTPS
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # Domain
    r'localhost|'  # localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
    r'(?::\d+)?'  # Optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)


def validate_email(email: str) -> bool:
    """Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid email format
    """
    if not email or len(email) > 254:  # RFC 5321
        return False
    
    # Check basic format
    if not EMAIL_REGEX.match(email):
        return False
    
    # Additional checks
    local, domain = email.rsplit('@', 1)
    
    # Local part checks
    if len(local) > 64:  # RFC 5321
        return False
    if local.startswith('.') or local.endswith('.'):
        return False
    if '..' in local:
        return False
    
    # Domain checks
    if len(domain) > 253:
        return False
    if domain.startswith('.') or domain.endswith('.'):
        return False
    if '..' in domain:
        return False
    
    return True


def validate_url(url: str) -> bool:
    """Basic URL format validation.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid URL format
        
    Note:
        For security-critical validation, use URLValidator class instead.
    """
    if not url or len(url) > 2048:
        return False
    
    return bool(URL_REGEX.match(url))


class InputSanitizer:
    """Sanitizes user input to prevent injection attacks."""
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 2000) -> str:
        """Sanitize text input.
        
        Args:
            text: Text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Truncate to max length
        text = text[:max_length]
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters (except newline and tab)
        cleaned = ''.join(
            char for char in text
            if char == '\n' or char == '\t' or not ord(char) < 32
        )
        
        # HTML escape for safety (basic)
        # IMPORTANT: Escape & first to avoid double-escaping
        cleaned = cleaned.replace('&', '&amp;')
        cleaned = cleaned.replace('<', '&lt;')
        cleaned = cleaned.replace('>', '&gt;')
        cleaned = cleaned.replace('"', '&quot;')
        cleaned = cleaned.replace("'", '&#x27;')
        
        return cleaned
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal.
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            Sanitized filename
        """
        if not filename:
            return "unnamed"
        
        # Remove path separators and null bytes
        filename = filename.replace('/', '').replace('\\', '').replace('\x00', '')
        
        # Remove special characters
        filename = re.sub(r'[^\w\s.-]', '', filename)
        
        # Remove leading dots (hidden files)
        filename = filename.lstrip('.')
        
        # Limit length
        name, ext = os.path.splitext(filename)
        if len(name) > 200:
            name = name[:200]
        if len(ext) > 10:
            ext = ext[:10]
        
        filename = name + ext
        
        # Ensure not empty
        if not filename:
            filename = "unnamed"
        
        return filename