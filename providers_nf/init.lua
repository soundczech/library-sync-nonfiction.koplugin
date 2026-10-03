local providers = {
    grimmory = require("providers_nf/grimmory"),
    bookorbit = require("providers_nf/bookorbit"),
}

function providers.get(id)
    return providers[id] or providers.grimmory
end

function providers.isValid(id)
    return providers[id] ~= nil
end

return providers
