package supplychain.issuer_subject

import future.keywords.if

default allow := false

allow if {
	regex.match(input.policy.allowed_issuer_regex, input.issuer)
	regex.match(input.policy.allowed_subject_regex, input.subject)
}

reason := msg if {
	not allow
	msg := sprintf("issuer %s or subject %s failed allowlist", [input.issuer, input.subject])
}
