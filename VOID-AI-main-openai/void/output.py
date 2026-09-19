import re


class VoidOutput:

    @staticmethod
    def format(text):
        if not text:
            return ""

        text = str(text).replace("\r\n", "\n").replace("\r", "\n")

        lines = text.split("\n")
        output = []

        in_code = False
        code_buffer = []

        for line in lines:

            stripped = line.strip()

            # Code fences
            if stripped.startswith("```"):

                if in_code:
                    output.append("")
                    output.extend(
                        "  " + code_line
                        for code_line in code_buffer
                    )
                    output.append("")
                    code_buffer = []
                    in_code = False

                else:
                    in_code = True

                continue

            if in_code:
                code_buffer.append(line)
                continue

            # Markdown headings
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip()

                if heading:
                    if output and output[-1] != "":
                        output.append("")
                    output.append(
                        f"◆ {heading.upper()}"
                    )
                    output.append("")

                continue

            # Markdown horizontal rules
            if re.fullmatch(r"[-*_]{3,}", stripped):
                output.append(
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                continue

            # Markdown table separator
            if (
                "|" in stripped
                and re.fullmatch(
                    r"[\s|:\-]+",
                    stripped
                )
            ):
                continue

            # Markdown table rows
            if stripped.startswith("|") and stripped.endswith("|"):

                cells = [
                    cell.strip()
                    for cell in stripped.strip("|").split("|")
                ]

                cells = [
                    re.sub(r"\*\*(.*?)\*\*", r"\1", cell)
                    for cell in cells
                ]

                if cells:
                    if len(cells) == 2:
                        output.append(
                            f"• {cells[0]}: {cells[1]}"
                        )
                    else:
                        output.append(
                            "• " + " | ".join(cells)
                        )

                continue

            # Bold
            line = re.sub(
                r"\*\*(.*?)\*\*",
                r"\1",
                line
            )

            # Italic
            line = re.sub(
                r"(?<!\*)\*(.*?)\*(?!\*)",
                r"\1",
                line
            )

            # Inline code
            line = re.sub(
                r"`([^`]+)`",
                r"\1",
                line
            )

            # Numbered lists
            match = re.match(
                r"^\s*(\d+)\.\s+(.*)",
                line
            )

            if match:
                output.append(
                    f"{match.group(1)}. {match.group(2)}"
                )
                continue

            # Bullet lists
            match = re.match(
                r"^\s*[-*+]\s+(.*)",
                line
            )

            if match:
                output.append(
                    f"• {match.group(1)}"
                )
                continue

            output.append(line)

        if in_code and code_buffer:
            output.append("")
            output.extend(
                "  " + code_line
                for code_line in code_buffer
            )

        # Remove excessive blank lines
        cleaned = []

        blank_count = 0

        for line in output:

            if not line.strip():
                blank_count += 1

                if blank_count <= 2:
                    cleaned.append("")

            else:
                blank_count = 0
                cleaned.append(line.rstrip())

        return "\n".join(cleaned).strip()
