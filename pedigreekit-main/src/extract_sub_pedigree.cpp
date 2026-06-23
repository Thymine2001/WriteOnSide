#include <Rcpp.h>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <string>
#include <algorithm>
#include <cctype>

using namespace Rcpp;

namespace {

inline std::string trim_copy(const std::string& x) {
  size_t start = 0;
  while (start < x.size() && std::isspace(static_cast<unsigned char>(x[start]))) {
    ++start;
  }
  if (start == x.size()) return "";

  size_t end = x.size() - 1;
  while (end > start && std::isspace(static_cast<unsigned char>(x[end]))) {
    --end;
  }
  return x.substr(start, end - start + 1);
}

inline std::string normalize_key(const std::string& x) {
  std::string out = trim_copy(x);
  std::transform(out.begin(), out.end(), out.begin(), [](unsigned char ch) {
    return static_cast<char>(std::tolower(ch));
  });
  return out;
}

inline bool is_missing_value(const std::string& x,
                             const std::unordered_set<std::string>& missing_set) {
  if (x.empty()) return true;
  return missing_set.find(normalize_key(x)) != missing_set.end();
}

}  // namespace

// [[Rcpp::export]]
LogicalVector fast_extract_sub_pedigree_cpp(CharacterVector ids,
                                             CharacterVector sires,
                                             CharacterVector dams,
                                             CharacterVector target_ids,
                                             int max_depth,
                                             CharacterVector missing) {
  const int n = ids.size();

  std::unordered_map<std::string, int> id_to_index;
  id_to_index.reserve(static_cast<size_t>(n) * 2);

  std::vector<std::string> ids_str(n);
  std::vector<std::string> sires_str(n);
  std::vector<std::string> dams_str(n);

  for (int i = 0; i < n; ++i) {
    std::string id = Rcpp::as<std::string>(ids[i]);
    std::string sire = Rcpp::as<std::string>(sires[i]);
    std::string dam = Rcpp::as<std::string>(dams[i]);

    ids_str[i] = id;
    sires_str[i] = sire;
    dams_str[i] = dam;

    if (id_to_index.find(id) == id_to_index.end()) {
      id_to_index[id] = i;
    }
  }

  std::unordered_set<std::string> missing_set;
  missing_set.reserve(static_cast<size_t>(missing.size()) + 4);
  for (int i = 0; i < missing.size(); ++i) {
    std::string m = Rcpp::as<std::string>(missing[i]);
    missing_set.insert(normalize_key(m));
  }
  missing_set.insert("");

  std::unordered_set<std::string> selected;
  selected.reserve(static_cast<size_t>(n));

  std::vector<std::string> frontier;
  frontier.reserve(static_cast<size_t>(target_ids.size()));

  for (int i = 0; i < target_ids.size(); ++i) {
    std::string t = trim_copy(Rcpp::as<std::string>(target_ids[i]));
    if (is_missing_value(t, missing_set)) continue;

    auto it = id_to_index.find(t);
    if (it == id_to_index.end()) continue;

    if (selected.insert(t).second) {
      frontier.push_back(t);
    }
  }

  bool all_generation = (max_depth < 0);
  int depth = 0;

  while (!frontier.empty() && (all_generation || depth < max_depth)) {
    std::vector<std::string> next_frontier;
    next_frontier.reserve(frontier.size() * 2);

    for (const std::string& id : frontier) {
      auto idx_it = id_to_index.find(id);
      if (idx_it == id_to_index.end()) continue;

      const int idx = idx_it->second;
      const std::string& sire = sires_str[idx];
      const std::string& dam = dams_str[idx];

      if (!is_missing_value(sire, missing_set) && id_to_index.find(sire) != id_to_index.end()) {
        if (selected.insert(sire).second) {
          next_frontier.push_back(sire);
        }
      }
      if (!is_missing_value(dam, missing_set) && id_to_index.find(dam) != id_to_index.end()) {
        if (selected.insert(dam).second) {
          next_frontier.push_back(dam);
        }
      }
    }

    frontier.swap(next_frontier);
    ++depth;
  }

  LogicalVector keep(n, false);
  for (int i = 0; i < n; ++i) {
    keep[i] = (selected.find(ids_str[i]) != selected.end());
  }

  return keep;
}
