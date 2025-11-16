"hidden_first_name": "",
        "hidden_mid_name": "",
        "vk_id": "",
        "subject_id": "20",
        "course_id": "1856",
        "module_id": module_id,
        "lesson_id": lesson_id,
    }

    resp = s.get(student_live_url, params=params, headers=headers, timeout=15)

    # CAPCHA DETECT
    if "captcha" in resp.text.lower() or "робот" in resp.text.lower():
        logger.error("❌ CAPTCHA DETECTED — сайт требует проверку!")
        print(resp.text[:500])
        setattr(resp, "parsed_homeworks", [])
        return resp

    # =============================== PAGINATION =================================
    parsed = []

    def parse_page(html):
        soup = BeautifulSoup(html, "html.parser")
        tbody = soup.find("tbody", id="student_lives_body")
        if not tbody:
            return []

        data = []
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            for a in tr.find_all("a", href=True):
                href = a["href"]
                if "student_live/tasks" not in href:
                    continue

                spans = [sp.get_text(strip=True) for sp in a.find_all("span")]

                b = tr.find("b", attrs={"data-datetime": True})
                dt = b.get("data-datetime") if b else None

                data.append((href, spans, dt))

        return data

    html = resp.text
    parsed.extend(parse_page(html))

    # Пагинация
    page_num = 1
    while True:
        soup = BeautifulSoup(html, "html.parser")

        pagination = soup.find("ul", class_="pagination")
        next_link = None
        if pagination:
            for a in pagination.find_all("a", href=True):
                if f"page={page_num+1}" in a["href"]:
                    next_link = urljoin(student_live_url, a["href"])
                    break

        if not next_link:
            break

        time.sleep(random.uniform(0.5, 1.1))
        next_resp = s.get(next_link, headers=headers, timeout=15)
        html = next_resp.text

        parsed.extend(parse_page(html))
        page_num += 1

    logger.info("Parsed %d homework links", len(parsed))

    setattr(resp, "parsed_homeworks", parsed)
    return resp
