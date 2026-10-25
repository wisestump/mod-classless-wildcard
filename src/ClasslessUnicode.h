#ifndef CLASSLESS_WILDCARD_UNICODE_H
#define CLASSLESS_WILDCARD_UNICODE_H

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace ClasslessWildcard
{
    namespace Unicode
    {
        // Spell names come from UTF-8 DBC strings. Fold the alphabets used by
        // the addon locales before comparing code points; byte-wise std::string
        // ordering makes uppercase Cyrillic names sort separately from lowercase.
        inline std::uint32_t FoldCase(std::uint32_t codepoint)
        {
            if (codepoint >= 'A' && codepoint <= 'Z')
                return codepoint + ('a' - 'A');
            if ((codepoint >= 0x00C0 && codepoint <= 0x00D6)
                || (codepoint >= 0x00D8 && codepoint <= 0x00DE))
                return codepoint + 0x20;
            if (codepoint == 0x0178)
                return 0x00FF;
            if (codepoint >= 0x0400 && codepoint <= 0x040F)
                return codepoint + 0x50;
            if (codepoint >= 0x0410 && codepoint <= 0x042F)
                return codepoint + 0x20;
            return codepoint;
        }

        inline std::vector<std::uint32_t> FoldedCodepoints(std::string const& text)
        {
            std::vector<std::uint32_t> result;
            for (std::size_t i = 0; i < text.size();)
            {
                std::uint8_t const lead = static_cast<std::uint8_t>(text[i]);
                std::uint32_t codepoint = lead;
                std::size_t length = 1;
                if (lead >= 0xC2 && lead <= 0xDF)
                {
                    codepoint = lead & 0x1F;
                    length = 2;
                }
                else if (lead >= 0xE0 && lead <= 0xEF)
                {
                    codepoint = lead & 0x0F;
                    length = 3;
                }
                else if (lead >= 0xF0 && lead <= 0xF4)
                {
                    codepoint = lead & 0x07;
                    length = 4;
                }

                bool valid = length > 1 && i + length <= text.size();
                if (valid)
                    for (std::size_t j = 1; j < length; ++j)
                    {
                        std::uint8_t const continuation = static_cast<std::uint8_t>(text[i + j]);
                        if ((continuation & 0xC0) != 0x80)
                        {
                            valid = false;
                            break;
                        }
                        codepoint = (codepoint << 6) | (continuation & 0x3F);
                    }
                // Keep malformed input ordered deterministically and avoid
                // consuming a following byte that may start a valid sequence.
                if (!valid)
                {
                    codepoint = lead;
                    length = 1;
                }
                result.push_back(FoldCase(codepoint));
                i += length;
            }
            return result;
        }

        inline bool CaseInsensitiveLess(std::string const& left, std::string const& right)
        {
            std::vector<std::uint32_t> const foldedLeft = FoldedCodepoints(left);
            std::vector<std::uint32_t> const foldedRight = FoldedCodepoints(right);
            return std::lexicographical_compare(foldedLeft.begin(), foldedLeft.end(),
                                                foldedRight.begin(), foldedRight.end());
        }
    }
}

#endif
