url = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB"
try:
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers).json()
    print("Categories:")
    for node in res:
        print(f"{node['id']}: {node['text']}")
        # Let's get the first table inside this node
        try:
            sub = requests.get(f"{url}/{node['id']}", headers=headers).json()
            if sub:
                sub_node = sub[0]
                if sub_node['type'] == 'l':
                    sub2 = requests.get(f"{url}/{node['id']}/{sub_node['id']}", headers=headers).json()
                    if sub2 and sub2[0]['type'] == 't':
                        print(f"  Found table: DB/{node['id']}/{sub_node['id']}/{sub2[0]['id']}")
                elif sub_node['type'] == 't':
                    print(f"  Found table: DB/{node['id']}/{sub_node['id']}")
        except Exception as e:
            pass
except Exception as e:
    print("Error:", e)
