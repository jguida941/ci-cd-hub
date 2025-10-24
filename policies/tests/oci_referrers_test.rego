package supplychain.oci_referrers_test

import data.supplychain.oci_referrers

test_allow_when_all_referrers_present {
  oci_referrers.allow with input as {"cyclonedx": true, "spdx": true, "provenance": true}
}

test_missing_referrers_detected {
  not oci_referrers.allow with input as {"cyclonedx": true, "spdx": true}
  oci_referrers.missing["provenance"] with input as {"cyclonedx": true, "spdx": true}
}
