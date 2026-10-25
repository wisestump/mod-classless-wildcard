local fallback = ClasslessWildcardLocaleData or {}
local localized = GetLocale() == "ruRU" and ClasslessWildcardLocaleData_ruRU or nil

local function merge(base, override)
    local out = {}
    for key, value in pairs(base or {}) do out[key] = value end
    for key, value in pairs(override or {}) do
        if type(value) == "table" and type(out[key]) == "table" then
            local nested = {}
            for subkey, subvalue in pairs(out[key]) do nested[subkey] = subvalue end
            for subkey, subvalue in pairs(value) do nested[subkey] = subvalue end
            out[key] = nested
        else
            out[key] = value
        end
    end
    return out
end

ClasslessWildcardLocale = merge(fallback, localized)
