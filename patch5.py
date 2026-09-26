import glob
import re

html_files = glob.glob(r'd:\xerox\templates\*.html')

fix_script = """
        // Global Fetch interceptor to fix BE to CE dates in query params
        const originalFetch = window.fetch;
        window.fetch = async function() {
            let [resource, config] = arguments;
            if (typeof resource === 'string' && resource.includes('?')) {
                resource = resource.replace(/([?&](?:start_date|end_date)=)(\d{4})(-\d{2}-\d{2})/g, function(match, p1, p2, p3) {
                    let year = parseInt(p2);
                    if (year > 2400) year -= 543;
                    return p1 + year + p3;
                });
            }
            return originalFetch(resource, config);
        };
"""

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if "originalFetch = window.fetch" not in content:
        # Inject right before the closing script tag of the global UI scripts
        content = content.replace('// Currency Formatter', fix_script + '\n        // Currency Formatter')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

print("Patch 5 complete.")
