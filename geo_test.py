from web_scraper import extract_geolocation_data, extract_contact_information
import json

# Sample HTML with geolocation data
test_html = """
<html>
<head>
    <meta property="og:latitude" content="40.7128" />
    <meta property="og:longitude" content="-74.0060" />
    <meta property="og:locality" content="New York City" />
    <meta property="og:country-name" content="USA" />
    <title>Test Geolocation Data</title>
</head>
<body>
    <h1>Sample location data</h1>
    <p>Our headquarters is located at 123 Main Street, New York City, NY 10001, USA.</p>
    <p>Contact us at: info@example.com or call +1 (555) 123-4567.</p>
    <p>The GPS coordinates are: 40.7128, -74.0060</p>
    <iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d193595.15830869428!2d-74.11976397304605!3d40.69766374874431!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x89c24fa5d33f083b%3A0xc80b8f06e177fe62!2sNew%20York%2C%20NY%2C%20USA!5e0!3m2!1sen!2sin!4v1606815826814!5m2!1sen!2sin" width="600" height="450" frameborder="0" style="border:0;" allowfullscreen="" aria-hidden="false" tabindex="0"></iframe>
</body>
</html>
"""

# Test cryptocurrency HTML
crypto_html = """
<html>
<body>
    <h1>Cryptocurrency Information</h1>
    <p>Bitcoin Wallet: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa</p>
    <p>Ethereum Address: 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045</p>
    <p>For privacy, we also offer a Tor hidden service at https://expyuzz4wqqyqhjn.onion</p>
</body>
</html>
"""

# Test dark web detection
darkweb_html = """
<html>
<body>
    <h1>Secure Communications</h1>
    <p>To access our secure resources, visit our Tor hidden service at https://expyuzz4wqqyqhjn.onion</p>
    <p>Username: secure_osint_researcher</p>
    <p>Connect with us on secure messaging platforms:</p>
    <ul>
        <li>Signal: +1 (555) 123-4567</li>
        <li>ProtonMail: secure@protonmail.com</li>
        <li>Session ID: 05b3e1e10aecf19316e7faf8ccb7ddcfa0249d35cd4b971f09f6d2b171e9570926</li>
    </ul>
</body>
</html>
"""

# Test contact information
contact_html = """
<html>
<body>
    <h1>Contact Information</h1>
    <div class="contact-info">
        <p>Email: contact@example.com, support@example.com</p>
        <p>Phone: +1 (555) 123-4567, 555-987-6543</p>
        <div class="address">
            123 Main Street, Suite 456<br>
            New York, NY 10001<br>
            United States
        </div>
        <p>Social Media:</p>
        <ul>
            <li>Twitter: @example_company</li>
            <li>LinkedIn: linkedin.com/company/example-company</li>
            <li>GitHub: github.com/example-company</li>
        </ul>
    </div>
</body>
</html>
"""

# Test all extractors
print("\n=== GEOLOCATION DATA ===")
geo_data = extract_geolocation_data(test_html)
print(json.dumps(geo_data, indent=2))

print("\n=== CONTACT INFORMATION ===")
contact_data = extract_contact_information(contact_html)
print(json.dumps(contact_data, indent=2))

print("\n=== CRYPTOCURRENCY DETECTION ===")
# Use our existing functions to extract cryptocurrency data
from assets import extract_social_profiles_from_text
crypto_text = "Bitcoin Wallet: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\nEthereum Address: 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
crypto_data = extract_social_profiles_from_text(crypto_text)
print(json.dumps(crypto_data, indent=2))

print("\n=== DARK WEB DETECTION ===")
# Try a more formatted dark web reference with the specific pattern our code looks for
dark_web_text = """
To access our secure resources:
- Onion Service: https://expyuzz4wqqyqhjn.onion
- Connect on Tor using username: secure_osint_researcher
- Bitcoin payment address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
- For secure chat, find me on the dark web: underground_investigator
"""

# Use our existing functions to extract dark web data
dark_web_data = extract_social_profiles_from_text(dark_web_text)

# Also try extracting usernames which would catch the tor username
from assets import extract_usernames_from_text
dark_web_usernames = extract_usernames_from_text(dark_web_text)

print("Social profiles:")
print(json.dumps(dark_web_data, indent=2))
print("\nDetected usernames:")
print(json.dumps(dark_web_usernames, indent=2))