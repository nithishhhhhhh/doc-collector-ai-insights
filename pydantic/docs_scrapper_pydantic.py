import os
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

VERSIONS = [
    "dev", "2.11", "2.10", "2.9", "2.8", "2.7", "2.6",
    "2.5", "2.4"
]

TOPIC_PATHS = [
    # API Core
    "api/base_model/", "api/root_model/", "api/dataclasses/",
    "api/type_adapter/", "api/validate_call/", "api/fields/", "api/aliases/",
    "api/configuration/", "api/json_schema/", "api/errors/", "api/functional_validators/",
    "api/functional_serializers/", "api/standard_library_types/", "api/pydantic_types/",
    "api/network_types/", "api/version_information/", "api/annotated_handlers/",
    "api/experimental/", "api/pydantic_core/", "api/pydantic_core.core_schema/",
    "api/pydantic_settings/",

    # Extra Types
    "api/pydantic_extra_types_color/",
    "api/pydantic_extra_types_country/",
    "api/pydantic_extra_types_payment/",
    "api/pydantic_extra_types_phone_numbers/",
    "api/pydantic_extra_types_routing_numbers/",
    "api/pydantic_extra_types_coordinate/",
    "api/pydantic_extra_types_mac_address/",
    "api/pydantic_extra_types_isbn/",
    "api/pydantic_extra_types_pendulum_dt/",
    "api/pydantic_extra_types_currency_code/",
    "api/pydantic_extra_types_language_code/",
    "api/pydantic_extra_types_script_code/",
    "api/pydantic_extra_types_semantic_version/",
    "api/pydantic_extra_types_timezone_name/",
    "api/pydantic_extra_types_ulid/",

    # Concepts
    "concepts/models/",
    "concepts/fields/",
    "concepts/json_schema/",
    "concepts/json/",
    "concepts/types/",
    "concepts/unions/",
    "concepts/alias/",
    "concepts/config/",
    "concepts/serialization/",
    "concepts/validators/",
    "concepts/dataclasses/",
    "concepts/forward_annotations/",
    "concepts/strict_mode/",
    "concepts/type_adapter/",
    "concepts/validation_decorator/",
    "concepts/conversion_table/",
    "concepts/pydantic_settings/",
    "concepts/performance/",
    "concepts/experimental/",

    # Internals & Errors
    "internals/architecture/", "internals/resolving_annotations/",
    "examples/files/", "examples/requests/", "examples/queues/",
    "examples/orms/", "examples/custom_validators/"
    "errors/errors/", "errors/validation_errors/", "errors/usage_errors/",

    # Integrations
    "integrations/logfire/", "integrations/llms/", 
    "integrations/mypy/", "integrations/pycharm/", "integrations/hypothesis/",
    "integrations/visual_studio_code/", "integrations/datamodel_code_generator/",
    "integrations/devtools/", "integrations/rich/", "integrations/linting/",
    "integrations/documentation/", 
    "integrations/aws_lambda/",

    # Main doc pages
    "", "why/", "help_with_pydantic/", "install/", "migration/",
    "version-policy/", "contributing/", "changelog/"
]


def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def extract_clean_text(driver):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    main = soup.find("main") or soup.find("article") or soup.find(class_="md-content")
    if not main:
        return ""
    for tag in main(["nav", "header", "footer", "script", "style"]):
        tag.decompose()
    return main.get_text(separator="\n", strip=True)

def save_content(version, topic_name, text, url):
    safe_topic = re.sub(r'[^a-zA-Z0-9_-]', '_', topic_name)
    version_dir = f"pydantic_{version}_pages"
    os.makedirs(version_dir, exist_ok=True)

    file_path = os.path.join(version_dir, f"{safe_topic}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"{topic_name}\n{'=' * len(topic_name)}\nURL: {url}\n\n{text.strip()}\n")

    llm_path = f"llm_{version}.txt"
    with open(llm_path, "a", encoding="utf-8") as f:
        f.write(f"\n\n--- {topic_name} ---\nURL: {url}\n\n{text.strip()}\n")

def scrape_version(version):
    print(f"\n📘 Scraping Pydantic {version}")
    base_url = f"https://docs.pydantic.dev/{version}/"
    driver = setup_driver()

    try:
        for topic_path in TOPIC_PATHS:
            topic_name = topic_path.strip("/").replace("/", " ").replace("_", " ").title() or "Welcome"
            url = base_url + topic_path
            print(f"🔗 {topic_name} ({url})")

            try:
                driver.get(url)
                time.sleep(2)
                text = extract_clean_text(driver)
                if len(text.strip()) < 100:
                    print("⚠️  Skipped (too short or empty)")
                    continue
                save_content(version, topic_name, text, url)
            except Exception as e:
                print(f"❌ Error scraping {url}: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    for version in VERSIONS:
        scrape_version(version)

    print("\n✅ All versions scraped and saved.")
