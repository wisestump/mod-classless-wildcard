#include "../src/ClasslessUnicode.h"

#include <cassert>
#include <string>

int main()
{
    using ClasslessWildcard::Unicode::CaseInsensitiveLess;

    assert(!CaseInsensitiveLess("\xD0\xAF", "\xD0\xB0")); // Я / а
    assert(CaseInsensitiveLess("\xD0\x90", "\xD0\xB1")); // А / б
    assert(!CaseInsensitiveLess("\xD0\xB0", "\xD0\x90")); // а / А
    assert(!CaseInsensitiveLess("\xD0\xA4\xD0\xBB\xD0\x90\xD1\x88",
                                "\xD1\x84\xD0\xBB\xD0\xB0\xD1\x88")); // ФлАш / флаш
    assert(!CaseInsensitiveLess("\xD1\x84\xD0\xBB\xD0\xB0\xD1\x88",
                                "\xD0\xA4\xD0\xBB\xD0\x90\xD1\x88"));
    assert(!CaseInsensitiveLess("\xD0\x81\xD0\xBB\xD0\xBA\xD0\xB0",
                                "\xD1\x91\xD0\xBB\xD0\xBA\xD0\xB0")); // Ёлка / ёлка
    assert(!CaseInsensitiveLess("\xD1\x91\xD0\xB6", "\xD0\x95\xD0\xBB\xD1\x8C")); // ёж / Ель
    assert(CaseInsensitiveLess("Arcane", "Броня"));
    assert(!CaseInsensitiveLess("FIRE", "fire"));
}
