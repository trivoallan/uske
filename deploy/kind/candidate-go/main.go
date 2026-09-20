// A demo candidate for Dependency-Track: its only dependency, golang.org/x/text, is pinned on
// a version with known advisories (GO-2021-0113, GO-2022-1059). Used, so it lands in the binary.
package main

import (
	"fmt"

	"golang.org/x/text/language"
)

func main() {
	fmt.Println(language.Make("fr-FR"))
}
