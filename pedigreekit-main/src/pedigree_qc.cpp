#include <Rcpp.h>
#ifdef _OPENMP
#include <omp.h>
#endif
#include <unordered_set>
#include <unordered_map>
#include <string>
#include <algorithm>
#include <random>
#include <functional>
#include <queue>
#include <cctype>
using namespace Rcpp;

// [[Rcpp::export]]
List fast_pedigree_qc(CharacterVector ids, 
                      CharacterVector sires, 
                      CharacterVector dams) {
  
  int n = ids.size();
  
  // Use unordered_set for O(1) lookup
  std::unordered_set<std::string> id_set;
  std::unordered_set<std::string> missing_sires_set;
  std::unordered_set<std::string> missing_dams_set;
  std::unordered_set<std::string> sires_mentioned_set;
  std::unordered_set<std::string> dams_mentioned_set;
  std::unordered_map<std::string, int> id_count;
  std::unordered_map<std::string, int> sire_progeny_count;
  std::unordered_map<std::string, int> dam_progeny_count;
  std::unordered_set<std::string> founder_set;
  id_set.reserve(n * 2);
  missing_sires_set.reserve(n);
  missing_dams_set.reserve(n);
  sires_mentioned_set.reserve(n);
  dams_mentioned_set.reserve(n);
  id_count.reserve(n * 2);
  sire_progeny_count.reserve(n);
  dam_progeny_count.reserve(n);
  founder_set.reserve(n);
  
  int founders = 0;
  int with_both_parents = 0;
  int only_sire_count = 0;
  int only_dam_count = 0;
  int self_parent_count = 0;
  std::vector<std::string> duplicate_ids;
  
  std::vector<std::string> ids_str(n);
  std::vector<std::string> sires_str(n);
  std::vector<std::string> dams_str(n);

  // First pass: build ID set and count duplicates
  for (int i = 0; i < n; i++) {
    std::string id = Rcpp::as<std::string>(ids[i]);
    std::string sire = Rcpp::as<std::string>(sires[i]);
    std::string dam = Rcpp::as<std::string>(dams[i]);
    ids_str[i] = id;
    sires_str[i] = sire;
    dams_str[i] = dam;
    id_set.insert(id);
    
    id_count[id]++;
    if (id_count[id] == 2) {
      duplicate_ids.push_back(id);
    }
  }
  
  // Second pass: analyze relationships
  for (int i = 0; i < n; i++) {
    const std::string& id = ids_str[i];
    const std::string& sire = sires_str[i];
    const std::string& dam = dams_str[i];
    
    bool has_sire = (sire != "NA" && sire != "0" && sire != "");
    bool has_dam = (dam != "NA" && dam != "0" && dam != "");
    
    // Count founders
    if (!has_sire && !has_dam) {
      founders++;
      founder_set.insert(id);
    }
    
    // Count with both parents / only sire / only dam
    if (has_sire && has_dam) {
      with_both_parents++;
    } else if (has_sire && !has_dam) {
      only_sire_count++;
    } else if (!has_sire && has_dam) {
      only_dam_count++;
    }
    
    // Check self-parenting
    if ((has_sire && sire == id) || (has_dam && dam == id)) {
      self_parent_count++;
    }
    
    // Check missing parents
    if (has_sire) {
      sires_mentioned_set.insert(sire);
      sire_progeny_count[sire]++;
    }
    if (has_dam) {
      dams_mentioned_set.insert(dam);
      dam_progeny_count[dam]++;
    }
    
    if (has_sire && id_set.find(sire) == id_set.end()) {
      missing_sires_set.insert(sire);
    }
    if (has_dam && id_set.find(dam) == id_set.end()) {
      missing_dams_set.insert(dam);
    }
  }
  
  // Convert sets to vectors
  CharacterVector missing_sires(missing_sires_set.size());
  int idx = 0;
  for (const auto& s : missing_sires_set) {
    missing_sires[idx++] = s;
  }
  
  CharacterVector missing_dams(missing_dams_set.size());
  idx = 0;
  for (const auto& d : missing_dams_set) {
    missing_dams[idx++] = d;
  }
  
  CharacterVector duplicates(duplicate_ids.size());
  for (size_t i = 0; i < duplicate_ids.size(); i++) {
    duplicates[i] = duplicate_ids[i];
  }
  
  // Dual-role parent IDs (appear as both sire and dam)
  std::vector<std::string> dual_role_ids;
  for (const auto& s : sires_mentioned_set) {
    if (dams_mentioned_set.find(s) != dams_mentioned_set.end()) {
      dual_role_ids.push_back(s);
    }
  }
  CharacterVector dual_role(dual_role_ids.size());
  for (size_t i = 0; i < dual_role_ids.size(); i++) {
    dual_role[i] = dual_role_ids[i];
  }
  
  // Parent/progeny statistics
  int unique_sires = static_cast<int>(sire_progeny_count.size());
  int unique_dams = static_cast<int>(dam_progeny_count.size());
  long long total_sire_progeny = 0;
  long long total_dam_progeny = 0;
  for (const auto& kv : sire_progeny_count) total_sire_progeny += kv.second;
  for (const auto& kv : dam_progeny_count) total_dam_progeny += kv.second;
  
  std::unordered_set<std::string> parents_with_progeny;
  parents_with_progeny.reserve(sire_progeny_count.size() + dam_progeny_count.size());
  for (const auto& kv : sire_progeny_count) {
    if (id_set.find(kv.first) != id_set.end()) parents_with_progeny.insert(kv.first);
  }
  for (const auto& kv : dam_progeny_count) {
    if (id_set.find(kv.first) != id_set.end()) parents_with_progeny.insert(kv.first);
  }
  int individuals_with_progeny = static_cast<int>(parents_with_progeny.size());
  int individuals_without_progeny = n - individuals_with_progeny;
  
  int founder_sires = 0;
  int founder_dams = 0;
  long long founder_sire_progeny = 0;
  long long founder_dam_progeny = 0;
  std::unordered_set<std::string> founder_parent_ids;
  founder_parent_ids.reserve(founders);
  for (const auto& kv : sire_progeny_count) {
    if (founder_set.find(kv.first) != founder_set.end()) {
      founder_sires++;
      founder_sire_progeny += kv.second;
      founder_parent_ids.insert(kv.first);
    }
  }
  for (const auto& kv : dam_progeny_count) {
    if (founder_set.find(kv.first) != founder_set.end()) {
      founder_dams++;
      founder_dam_progeny += kv.second;
      founder_parent_ids.insert(kv.first);
    }
  }
  long long founder_total_progeny = 0;
  for (int i = 0; i < n; i++) {
    const std::string& sire = sires_str[i];
    const std::string& dam = dams_str[i];
    bool has_sire = (sire != "NA" && sire != "0" && sire != "");
    bool has_dam = (dam != "NA" && dam != "0" && dam != "");
    if ((has_sire && founder_set.find(sire) != founder_set.end()) ||
        (has_dam && founder_set.find(dam) != founder_set.end())) {
      founder_total_progeny++;
    }
  }
  int founder_no_progeny = founders - static_cast<int>(founder_parent_ids.size());
  
  int non_founder_sires = 0;
  int non_founder_dams = 0;
  long long non_founder_sire_progeny = 0;
  long long non_founder_dam_progeny = 0;
  for (const auto& kv : sire_progeny_count) {
    if (founder_set.find(kv.first) == founder_set.end()) {
      non_founder_sires++;
      non_founder_sire_progeny += kv.second;
    }
  }
  for (const auto& kv : dam_progeny_count) {
    if (founder_set.find(kv.first) == founder_set.end()) {
      non_founder_dams++;
      non_founder_dam_progeny += kv.second;
    }
  }
  
  return List::create(
    Named("total") = n,
    Named("founders") = founders,
    Named("with_both_parents") = with_both_parents,
    Named("only_sire") = only_sire_count,
    Named("only_dam") = only_dam_count,
    Named("self_parent_count") = self_parent_count,
    Named("duplicate_ids") = duplicates,
    Named("missing_sires") = missing_sires,
    Named("missing_dams") = missing_dams,
    Named("dual_role_ids") = dual_role,
    Named("unique_sires") = unique_sires,
    Named("unique_dams") = unique_dams,
    Named("total_sire_progeny") = total_sire_progeny,
    Named("total_dam_progeny") = total_dam_progeny,
    Named("individuals_with_progeny") = individuals_with_progeny,
    Named("individuals_without_progeny") = individuals_without_progeny,
    Named("founder_sires") = founder_sires,
    Named("founder_dams") = founder_dams,
    Named("founder_sire_progeny") = founder_sire_progeny,
    Named("founder_dam_progeny") = founder_dam_progeny,
    Named("founder_total_progeny") = founder_total_progeny,
    Named("founder_no_progeny") = founder_no_progeny,
    Named("non_founder_sires") = non_founder_sires,
    Named("non_founder_dams") = non_founder_dams,
    Named("non_founder_sire_progeny") = non_founder_sire_progeny,
    Named("non_founder_dam_progeny") = non_founder_dam_progeny
  );
}

// [[Rcpp::export]]
List fast_pedigree_qc_sex(CharacterVector ids,
                          CharacterVector sires,
                          CharacterVector dams,
                          CharacterVector sex) {
  int n = ids.size();
  
  // Use unordered_set for O(1) lookup
  std::unordered_set<std::string> id_set;
  std::unordered_set<std::string> missing_sires_set;
  std::unordered_set<std::string> missing_dams_set;
  std::unordered_set<std::string> sires_mentioned_set;
  std::unordered_set<std::string> dams_mentioned_set;
  std::unordered_map<std::string, int> id_count;
  std::unordered_map<std::string, char> sex_map;
  std::unordered_map<std::string, int> sire_progeny_count;
  std::unordered_map<std::string, int> dam_progeny_count;
  std::unordered_set<std::string> founder_set;
  id_set.reserve(n * 2);
  missing_sires_set.reserve(n);
  missing_dams_set.reserve(n);
  sires_mentioned_set.reserve(n);
  dams_mentioned_set.reserve(n);
  id_count.reserve(n * 2);
  sex_map.reserve(n);
  sire_progeny_count.reserve(n);
  dam_progeny_count.reserve(n);
  founder_set.reserve(n);
  
  int founders = 0;
  int with_both_parents = 0;
  int only_sire_count = 0;
  int only_dam_count = 0;
  int self_parent_count = 0;
  std::vector<std::string> duplicate_ids;
  
  // Helper to normalize sex
  auto normalize_sex = [](std::string x) -> char {
    std::transform(x.begin(), x.end(), x.begin(), ::tolower);
    x.erase(0, x.find_first_not_of(" \t\r\n"));
    x.erase(x.find_last_not_of(" \t\r\n") + 1);
    if (x == "m" || x == "male" || x == "1") return 'M';
    if (x == "f" || x == "female" || x == "2") return 'F';
    return 0;
  };
  
  std::vector<std::string> ids_str(n);
  std::vector<std::string> sires_str(n);
  std::vector<std::string> dams_str(n);

  // First pass: build ID set and count duplicates, capture sex map
  for (int i = 0; i < n; i++) {
    std::string id = Rcpp::as<std::string>(ids[i]);
    std::string sire = Rcpp::as<std::string>(sires[i]);
    std::string dam = Rcpp::as<std::string>(dams[i]);
    ids_str[i] = id;
    sires_str[i] = sire;
    dams_str[i] = dam;
    id_set.insert(id);
    
    id_count[id]++;
    if (id_count[id] == 2) {
      duplicate_ids.push_back(id);
    }
    
    if (i < sex.size()) {
      std::string sx = Rcpp::as<std::string>(sex[i]);
      char s = normalize_sex(sx);
      if (s != 0) {
        sex_map[id] = s;
      }
    }
  }
  
  // Second pass: analyze relationships
  int sex_mismatch_sire = 0;
  int sex_mismatch_dam = 0;
  std::unordered_set<std::string> sex_mismatch_sire_ids;
  std::unordered_set<std::string> sex_mismatch_dam_ids;
  
  for (int i = 0; i < n; i++) {
    const std::string& id = ids_str[i];
    const std::string& sire = sires_str[i];
    const std::string& dam = dams_str[i];
    
    bool has_sire = (sire != "NA" && sire != "0" && sire != "");
    bool has_dam = (dam != "NA" && dam != "0" && dam != "");
    
    // Count founders
    if (!has_sire && !has_dam) {
      founders++;
      founder_set.insert(id);
    }
    
    // Count with both parents / only sire / only dam
    if (has_sire && has_dam) {
      with_both_parents++;
    } else if (has_sire && !has_dam) {
      only_sire_count++;
    } else if (!has_sire && has_dam) {
      only_dam_count++;
    }
    
    // Check self-parenting
    if ((has_sire && sire == id) || (has_dam && dam == id)) {
      self_parent_count++;
    }
    
    // Track mentioned parents
    if (has_sire) {
      sires_mentioned_set.insert(sire);
      sire_progeny_count[sire]++;
    }
    if (has_dam) {
      dams_mentioned_set.insert(dam);
      dam_progeny_count[dam]++;
    }
    
    // Check missing parents
    if (has_sire && id_set.find(sire) == id_set.end()) {
      missing_sires_set.insert(sire);
    }
    if (has_dam && id_set.find(dam) == id_set.end()) {
      missing_dams_set.insert(dam);
    }
    
    // Sex mismatch checks (if sex known for parent)
    if (has_sire) {
      auto it = sex_map.find(sire);
      if (it != sex_map.end() && it->second != 'M') {
        sex_mismatch_sire++;
        sex_mismatch_sire_ids.insert(sire);
      }
    }
    if (has_dam) {
      auto it = sex_map.find(dam);
      if (it != sex_map.end() && it->second != 'F') {
        sex_mismatch_dam++;
        sex_mismatch_dam_ids.insert(dam);
      }
    }
  }
  
  // Convert sets to vectors
  CharacterVector missing_sires(missing_sires_set.size());
  int idx = 0;
  for (const auto& s : missing_sires_set) {
    missing_sires[idx++] = s;
  }
  
  CharacterVector missing_dams(missing_dams_set.size());
  idx = 0;
  for (const auto& d : missing_dams_set) {
    missing_dams[idx++] = d;
  }
  
  CharacterVector duplicates(duplicate_ids.size());
  for (size_t i = 0; i < duplicate_ids.size(); i++) {
    duplicates[i] = duplicate_ids[i];
  }
  
  // Dual-role parent IDs (appear as both sire and dam)
  std::vector<std::string> dual_role_ids;
  for (const auto& s : sires_mentioned_set) {
    if (dams_mentioned_set.find(s) != dams_mentioned_set.end()) {
      dual_role_ids.push_back(s);
    }
  }
  CharacterVector dual_role(dual_role_ids.size());
  for (size_t i = 0; i < dual_role_ids.size(); i++) {
    dual_role[i] = dual_role_ids[i];
  }
  
  CharacterVector sex_mismatch_sire_vec(sex_mismatch_sire_ids.size());
  idx = 0;
  for (const auto& s : sex_mismatch_sire_ids) {
    sex_mismatch_sire_vec[idx++] = s;
  }
  
  CharacterVector sex_mismatch_dam_vec(sex_mismatch_dam_ids.size());
  idx = 0;
  for (const auto& d : sex_mismatch_dam_ids) {
    sex_mismatch_dam_vec[idx++] = d;
  }
  
  // Parent/progeny statistics
  int unique_sires = static_cast<int>(sire_progeny_count.size());
  int unique_dams = static_cast<int>(dam_progeny_count.size());
  long long total_sire_progeny = 0;
  long long total_dam_progeny = 0;
  for (const auto& kv : sire_progeny_count) total_sire_progeny += kv.second;
  for (const auto& kv : dam_progeny_count) total_dam_progeny += kv.second;
  
  std::unordered_set<std::string> parents_with_progeny;
  parents_with_progeny.reserve(sire_progeny_count.size() + dam_progeny_count.size());
  for (const auto& kv : sire_progeny_count) {
    if (id_set.find(kv.first) != id_set.end()) parents_with_progeny.insert(kv.first);
  }
  for (const auto& kv : dam_progeny_count) {
    if (id_set.find(kv.first) != id_set.end()) parents_with_progeny.insert(kv.first);
  }
  int individuals_with_progeny = static_cast<int>(parents_with_progeny.size());
  int individuals_without_progeny = n - individuals_with_progeny;
  
  int founder_sires = 0;
  int founder_dams = 0;
  long long founder_sire_progeny = 0;
  long long founder_dam_progeny = 0;
  std::unordered_set<std::string> founder_parent_ids;
  founder_parent_ids.reserve(founders);
  for (const auto& kv : sire_progeny_count) {
    if (founder_set.find(kv.first) != founder_set.end()) {
      founder_sires++;
      founder_sire_progeny += kv.second;
      founder_parent_ids.insert(kv.first);
    }
  }
  for (const auto& kv : dam_progeny_count) {
    if (founder_set.find(kv.first) != founder_set.end()) {
      founder_dams++;
      founder_dam_progeny += kv.second;
      founder_parent_ids.insert(kv.first);
    }
  }
  long long founder_total_progeny = 0;
  for (int i = 0; i < n; i++) {
    const std::string& sire = sires_str[i];
    const std::string& dam = dams_str[i];
    bool has_sire = (sire != "NA" && sire != "0" && sire != "");
    bool has_dam = (dam != "NA" && dam != "0" && dam != "");
    if ((has_sire && founder_set.find(sire) != founder_set.end()) ||
        (has_dam && founder_set.find(dam) != founder_set.end())) {
      founder_total_progeny++;
    }
  }
  int founder_no_progeny = founders - static_cast<int>(founder_parent_ids.size());
  
  int non_founder_sires = 0;
  int non_founder_dams = 0;
  long long non_founder_sire_progeny = 0;
  long long non_founder_dam_progeny = 0;
  for (const auto& kv : sire_progeny_count) {
    if (founder_set.find(kv.first) == founder_set.end()) {
      non_founder_sires++;
      non_founder_sire_progeny += kv.second;
    }
  }
  for (const auto& kv : dam_progeny_count) {
    if (founder_set.find(kv.first) == founder_set.end()) {
      non_founder_dams++;
      non_founder_dam_progeny += kv.second;
    }
  }
  
  return List::create(
    Named("total") = n,
    Named("founders") = founders,
    Named("with_both_parents") = with_both_parents,
    Named("only_sire") = only_sire_count,
    Named("only_dam") = only_dam_count,
    Named("self_parent_count") = self_parent_count,
    Named("duplicate_ids") = duplicates,
    Named("missing_sires") = missing_sires,
    Named("missing_dams") = missing_dams,
    Named("dual_role_ids") = dual_role,
    Named("sex_mismatch_sire_count") = sex_mismatch_sire,
    Named("sex_mismatch_dam_count") = sex_mismatch_dam,
    Named("sex_mismatch_sire_ids") = sex_mismatch_sire_vec,
    Named("sex_mismatch_dam_ids") = sex_mismatch_dam_vec,
    Named("unique_sires") = unique_sires,
    Named("unique_dams") = unique_dams,
    Named("total_sire_progeny") = total_sire_progeny,
    Named("total_dam_progeny") = total_dam_progeny,
    Named("individuals_with_progeny") = individuals_with_progeny,
    Named("individuals_without_progeny") = individuals_without_progeny,
    Named("founder_sires") = founder_sires,
    Named("founder_dams") = founder_dams,
    Named("founder_sire_progeny") = founder_sire_progeny,
    Named("founder_dam_progeny") = founder_dam_progeny,
    Named("founder_total_progeny") = founder_total_progeny,
    Named("founder_no_progeny") = founder_no_progeny,
    Named("non_founder_sires") = non_founder_sires,
    Named("non_founder_dams") = non_founder_dams,
    Named("non_founder_sire_progeny") = non_founder_sire_progeny,
    Named("non_founder_dam_progeny") = non_founder_dam_progeny
  );
}

// Fast loop detection using DFS
// [[Rcpp::export]]
List fast_detect_loops(CharacterVector ids, 
                       CharacterVector sires, 
                       CharacterVector dams) {
  
  int n = ids.size();
  
  // Build parent map: ID -> vector of parent IDs
  std::unordered_map<std::string, std::vector<std::string>> parent_map;
  std::unordered_set<std::string> id_set;
  parent_map.reserve(n);
  id_set.reserve(n * 2);

  std::vector<std::string> ids_str(n);
  std::vector<std::string> sires_str(n);
  std::vector<std::string> dams_str(n);
  
  // Populate ID set
  for (int i = 0; i < n; i++) {
    std::string id = Rcpp::as<std::string>(ids[i]);
    std::string sire = Rcpp::as<std::string>(sires[i]);
    std::string dam = Rcpp::as<std::string>(dams[i]);
    ids_str[i] = id;
    sires_str[i] = sire;
    dams_str[i] = dam;
    id_set.insert(id);
  }
  
  // Build parent relationships
  for (int i = 0; i < n; i++) {
    const std::string& id = ids_str[i];
    const std::string& sire = sires_str[i];
    const std::string& dam = dams_str[i];
    
    std::vector<std::string> parents;
    
    // Only add valid parent references
    if (sire != "NA" && sire != "0" && sire != "" && id_set.find(sire) != id_set.end()) {
      parents.push_back(sire);
    }
    if (dam != "NA" && dam != "0" && dam != "" && id_set.find(dam) != id_set.end()) {
      parents.push_back(dam);
    }
    
    if (!parents.empty()) {
      parent_map[id] = parents;
    }
  }
  
  // DFS-based cycle detection
  std::unordered_set<std::string> visited;
  std::unordered_set<std::string> rec_stack;
  std::vector<std::vector<std::string>> all_cycles;
  
  std::function<bool(const std::string&, std::vector<std::string>&)> dfs;
  dfs = [&](const std::string& node, std::vector<std::string>& path) -> bool {
    // Check if we found a cycle
    if (rec_stack.find(node) != rec_stack.end()) {
      // Extract cycle
      std::vector<std::string> cycle;
      bool in_cycle = false;
      for (const auto& p : path) {
        if (p == node) in_cycle = true;
        if (in_cycle) cycle.push_back(p);
      }
      cycle.push_back(node);
      all_cycles.push_back(cycle);
      return true;
    }
    
    // Already fully explored
    if (visited.find(node) != visited.end()) {
      return false;
    }
    
    // Mark as being processed
    rec_stack.insert(node);
    path.push_back(node);
    
    // Explore parents
    if (parent_map.find(node) != parent_map.end()) {
      for (const auto& parent : parent_map[node]) {
        dfs(parent, path);
      }
    }
    
    // Mark as fully explored
    path.pop_back();
    rec_stack.erase(node);
    visited.insert(node);
    
    return false;
  };
  
  // Check all nodes
  for (int i = 0; i < n; i++) {
    const std::string& id = ids_str[i];
    if (visited.find(id) == visited.end()) {
      std::vector<std::string> path;
      dfs(id, path);
    }
  }
  
  // Convert cycles to R list
  List cycles_list(all_cycles.size());
  for (size_t i = 0; i < all_cycles.size(); i++) {
    CharacterVector cycle(all_cycles[i].size());
    for (size_t j = 0; j < all_cycles[i].size(); j++) {
      cycle[j] = all_cycles[i][j];
    }
    cycles_list[i] = cycle;
  }
  
  return List::create(
    Named("count") = all_cycles.size(),
    Named("cycles") = cycles_list
  );
}

// Fast ancestor depth calculation with memoization
// [[Rcpp::export]]
List fast_find_deepest_ancestor(CharacterVector ids, 
                                CharacterVector sires, 
                                CharacterVector dams,
                                int sample_size = 200) {
  
  int n = ids.size();
  
  // Build lookup maps for O(1) access
  std::unordered_map<std::string, int> id_to_index;
  std::unordered_map<std::string, std::pair<std::string, std::string>> parent_map;
  std::vector<std::string> non_founders;
  id_to_index.reserve(n * 2);
  parent_map.reserve(n);
  non_founders.reserve(n);

  std::vector<std::string> ids_str(n);
  std::vector<std::string> sires_str(n);
  std::vector<std::string> dams_str(n);
  
  // First pass: build maps and identify non-founders
  for (int i = 0; i < n; i++) {
    std::string id = Rcpp::as<std::string>(ids[i]);
    std::string sire = Rcpp::as<std::string>(sires[i]);
    std::string dam = Rcpp::as<std::string>(dams[i]);
    ids_str[i] = id;
    sires_str[i] = sire;
    dams_str[i] = dam;
    
    id_to_index[id] = i;
    
    bool has_sire = (sire != "NA" && sire != "0" && sire != "");
    bool has_dam = (dam != "NA" && dam != "0" && dam != "");
    
    if (has_sire || has_dam) {
      non_founders.push_back(id);
      parent_map[id] = std::make_pair(
        has_sire ? sire : "",
        has_dam ? dam : ""
      );
    }
  }
  
  if (non_founders.empty()) {
    return List::create(
      Named("id") = CharacterVector(),
      Named("depth") = 0
    );
  }
  
  // Sample non-founders if needed
  std::vector<std::string> sample_ids;
  if (non_founders.size() > (size_t)sample_size) {
    // Random sampling using R's sample function
    Function sample("sample");
    IntegerVector indices = sample(non_founders.size(), sample_size, false);
    for (int i = 0; i < sample_size; i++) {
      int idx = indices[i] - 1; // R indices are 1-based
      if (idx >= 0 && idx < (int)non_founders.size()) {
        sample_ids.push_back(non_founders[idx]);
      }
    }
  } else {
    sample_ids = non_founders;
  }
  
  // Memoization: cache depth for each ID
  std::unordered_map<std::string, int> depth_cache;
  depth_cache.reserve(n);
  
  // Recursive function to calculate depth with cycle detection
  std::function<int(const std::string&, std::unordered_set<std::string>&, int)> calc_depth;
  calc_depth = [&](const std::string& id, std::unordered_set<std::string>& visited, int max_depth) -> int {
    // Check cache first
    if (depth_cache.find(id) != depth_cache.end()) {
      return depth_cache[id];
    }
    
    // Cycle detection
    if (visited.find(id) != visited.end()) {
      return 0;
    }
    
    // Max depth protection
    if (visited.size() > max_depth) {
      return visited.size();
    }
    
    // Check if ID exists
    if (parent_map.find(id) == parent_map.end()) {
      depth_cache[id] = 0;
      return 0;
    }
    
    auto parents = parent_map[id];
    bool has_sire = !parents.first.empty();
    bool has_dam = !parents.second.empty();
    
    // If no valid parents, this is a founder
    if (!has_sire && !has_dam) {
      depth_cache[id] = 0;
      return 0;
    }
    
    // Add to visited set
    visited.insert(id);
    
    int max_parent_depth = 0;
    
    // Calculate depth from sire
    if (has_sire && id_to_index.find(parents.first) != id_to_index.end()) {
      int sire_depth = calc_depth(parents.first, visited, max_depth);
      max_parent_depth = std::max(max_parent_depth, sire_depth);
    }
    
    // Calculate depth from dam
    if (has_dam && id_to_index.find(parents.second) != id_to_index.end()) {
      int dam_depth = calc_depth(parents.second, visited, max_depth);
      max_parent_depth = std::max(max_parent_depth, dam_depth);
    }
    
    // Remove from visited set
    visited.erase(id);
    
    int depth = max_parent_depth + 1;
    depth_cache[id] = depth;
    return depth;
  };
  
  // Calculate depth for all sampled individuals
  int max_depth = 0;
  std::string deepest_id = "";
  
  for (const auto& id : sample_ids) {
    std::unordered_set<std::string> visited;
    int depth = calc_depth(id, visited, 100);
    
    if (depth > max_depth) {
      max_depth = depth;
      deepest_id = id;
    }
  }
  
  if (deepest_id.empty() || max_depth == 0) {
    return List::create(
      Named("id") = CharacterVector(),
      Named("depth") = 0
    );
  }
  
  return List::create(
    Named("id") = deepest_id,
    Named("depth") = max_depth
  );
}

// Check birth date order: parents must be born before offspring
// [[Rcpp::export]]
List check_birth_date_order(CharacterVector ids,
                            CharacterVector sires,
                            CharacterVector dams,
                            NumericVector birth_dates) {
  // Function: Check if offspring birth dates are after their parents' birth dates
  // Parameters:
  //   ids: Individual ID vector
  //   sires: Sire ID vector
  //   dams: Dam ID vector
  //   birth_dates: Birth date vector (numeric, e.g., Date or POSIXct)
  // Returns: List containing detection results
  
  int n = ids.size();
  if (sires.size() != n || dams.size() != n || birth_dates.size() != n) {
    Rcpp::stop("Length mismatch: ids, sires, dams, and birth_dates must have same length.");
  }
  
  // Build ID to birth date mapping
  std::unordered_map<std::string, double> id_to_birthdate;
  for (int i = 0; i < n; i++) {
    std::string id = Rcpp::as<std::string>(ids[i]);
    if (!Rcpp::NumericVector::is_na(birth_dates[i])) {
      id_to_birthdate[id] = birth_dates[i];
    }
  }
  
  // Detect birth date order issues
  std::vector<std::string> invalid_offspring_ids;
  std::vector<std::string> invalid_sire_ids;
  std::vector<std::string> invalid_dam_ids;
  
  int invalid_count = 0;
  int invalid_sire_count = 0;
  int invalid_dam_count = 0;
  
  for (int i = 0; i < n; i++) {
    std::string id = Rcpp::as<std::string>(ids[i]);
    std::string sire = Rcpp::as<std::string>(sires[i]);
    std::string dam = Rcpp::as<std::string>(dams[i]);
    
    // Check if individual has birth date
    if (id_to_birthdate.find(id) == id_to_birthdate.end()) {
      continue;  // Skip individuals without birth dates
    }
    
    double offspring_date = id_to_birthdate[id];
    bool has_issue = false;
    std::string problem_sire = "";
    std::string problem_dam = "";
    
    // Check sire
    if (sire != "NA" && sire != "0" && sire != "" && id_to_birthdate.find(sire) != id_to_birthdate.end()) {
      double sire_date = id_to_birthdate[sire];
      if (offspring_date <= sire_date) {
        // Offspring birth date is not after sire's birth date
        problem_sire = sire;
        invalid_sire_count++;
        has_issue = true;
      }
    }
    
    // Check dam
    if (dam != "NA" && dam != "0" && dam != "" && id_to_birthdate.find(dam) != id_to_birthdate.end()) {
      double dam_date = id_to_birthdate[dam];
      if (offspring_date <= dam_date) {
        // Offspring birth date is not after dam's birth date
        problem_dam = dam;
        invalid_dam_count++;
        has_issue = true;
      }
    }
    
    if (has_issue) {
      invalid_offspring_ids.push_back(id);
      invalid_sire_ids.push_back(problem_sire);
      invalid_dam_ids.push_back(problem_dam);
      invalid_count++;
    }
  }
  
  // Convert to R vectors
  CharacterVector invalid_offspring(invalid_offspring_ids.size());
  CharacterVector invalid_sires(invalid_sire_ids.size());
  CharacterVector invalid_dams(invalid_dam_ids.size());
  
  for (size_t i = 0; i < invalid_offspring_ids.size(); i++) {
    invalid_offspring[i] = invalid_offspring_ids[i];
    invalid_sires[i] = invalid_sire_ids[i];
    invalid_dams[i] = invalid_dam_ids[i];
  }
  
  return List::create(
    Named("count") = invalid_count,
    Named("invalid_sire_count") = invalid_sire_count,
    Named("invalid_dam_count") = invalid_dam_count,
    Named("invalid_offspring_ids") = invalid_offspring,
    Named("invalid_sire_ids") = invalid_sires,
    Named("invalid_dam_ids") = invalid_dams
  );
}

// Fast LAP (Longest Ancestral Path) distribution calculation
// [[Rcpp::export]]
NumericVector fast_lap_distribution(CharacterVector ids,
                                    CharacterVector sires,
                                    CharacterVector dams,
                                    int sample_size = 10000,
                                    int max_depth = 20) {
  
  int n = ids.size();
  
  // Build lookup maps for O(1) access
  std::unordered_map<std::string, std::pair<std::string, std::string>> parent_map;
  std::unordered_set<std::string> id_set;
  std::vector<std::string> all_ids;
  parent_map.reserve(n);
  id_set.reserve(n * 2);
  all_ids.reserve(n);

  std::vector<std::string> ids_str(n);
  std::vector<std::string> sires_str(n);
  std::vector<std::string> dams_str(n);
  
  // First pass: build ID set
  for (int i = 0; i < n; i++) {
    std::string id = Rcpp::as<std::string>(ids[i]);
    std::string sire = Rcpp::as<std::string>(sires[i]);
    std::string dam = Rcpp::as<std::string>(dams[i]);
    ids_str[i] = id;
    sires_str[i] = sire;
    dams_str[i] = dam;
    id_set.insert(id);
    all_ids.push_back(id);
  }
  
  // Second pass: build parent map (treat non-empty parents as valid)
  for (int i = 0; i < n; i++) {
    const std::string& id = ids_str[i];
    const std::string& sire = sires_str[i];
    const std::string& dam = dams_str[i];
    
    bool has_sire = (sire != "NA" && sire != "0" && sire != "");
    bool has_dam = (dam != "NA" && dam != "0" && dam != "");
    
    if (has_sire || has_dam) {
      parent_map[id] = std::make_pair(
        has_sire ? sire : "",
        has_dam ? dam : ""
      );
    }
  }
  
  // Determine sample IDs
  std::vector<std::string> sample_ids;
  // Only sample for very large datasets (> 1000k); use 10k samples
  const int sample_threshold = 1000000;
  const int sample_target = 10000;
  if (n > sample_threshold) {
    Function sample("sample");
    IntegerVector indices = sample(n, sample_target, false);
    for (int i = 0; i < sample_target; i++) {
      int idx = indices[i] - 1; // R indices are 1-based
      if (idx >= 0 && idx < n) {
        sample_ids.push_back(all_ids[idx]);
      }
    }
  } else {
    sample_ids = all_ids;
  }
  
  // Memoization: cache depth for each ID
  std::unordered_map<std::string, int> depth_cache;
  depth_cache.reserve(n);
  
  // Recursive function to calculate LAP depth with cycle detection
  std::function<int(const std::string&, std::unordered_set<std::string>&)> calc_lap_depth;
  calc_lap_depth = [&](const std::string& id, std::unordered_set<std::string>& visited) -> int {
    // Check cache first
    if (depth_cache.find(id) != depth_cache.end()) {
      return depth_cache[id];
    }
    
    // Cycle detection
    if (visited.find(id) != visited.end()) {
      return 0; // Cycle detected, return 0 to avoid infinite recursion
    }
    
    // Check if ID has parents
    if (parent_map.find(id) == parent_map.end()) {
      depth_cache[id] = 0; // Founder
      return 0;
    }
    
    auto parents = parent_map[id];
    bool has_sire = !parents.first.empty();
    bool has_dam = !parents.second.empty();
    
    // If no valid parents, this is a founder
    if (!has_sire && !has_dam) {
      depth_cache[id] = 0;
      return 0;
    }
    
    // Add to visited set
    visited.insert(id);
    
    int max_parent_depth = 0;
    
    // Calculate depth from sire
    if (has_sire) {
      int sire_depth = calc_lap_depth(parents.first, visited);
      max_parent_depth = std::max(max_parent_depth, sire_depth);
    }
    
    // Calculate depth from dam
    if (has_dam) {
      int dam_depth = calc_lap_depth(parents.second, visited);
      max_parent_depth = std::max(max_parent_depth, dam_depth);
    }
    
    // Remove from visited set
    visited.erase(id);
    
    int depth = max_parent_depth + 1;
    // Cap depth at max_depth - 1 to fit distribution range
    if (depth >= max_depth) {
      depth = max_depth - 1;
    }
    depth_cache[id] = depth;
    return depth;
  };
  
  // Initialize distribution vector (0 to max_depth-1)
  std::vector<int> distribution(max_depth, 0);
  
  // Calculate LAP for all sampled individuals
  for (const auto& id : sample_ids) {
    std::unordered_set<std::string> visited;
    int depth = calc_lap_depth(id, visited);
    
    if (depth >= 0 && depth < max_depth) {
      distribution[depth]++;
    }
  }
  
  // Scale to total population if sampled
  double scale_factor = 1.0;
  if (n > (int)sample_ids.size() && sample_ids.size() > 0) {
    scale_factor = (double)n / (double)sample_ids.size();
  }
  
  // Convert to R numeric vector
  NumericVector result(max_depth);
  for (int i = 0; i < max_depth; i++) {
    result[i] = std::round(distribution[i] * scale_factor);
  }
  
  // Set names
  CharacterVector names_vec(max_depth);
  for (int i = 0; i < max_depth; i++) {
    names_vec[i] = std::to_string(i);
  }
  result.attr("names") = names_vec;
  
  return result;
}

// Fast LAP depth for each individual
// [[Rcpp::export]]
IntegerVector fast_lap_depths(CharacterVector ids,
                              CharacterVector sires,
                              CharacterVector dams) {
  int n = ids.size();
  
  std::unordered_set<std::string> id_set;
  std::unordered_map<std::string, std::pair<std::string, std::string>> parent_map;
  id_set.reserve(n * 2);
  parent_map.reserve(n);
  std::vector<std::string> ids_str(n);
  std::vector<std::string> sires_str(n);
  std::vector<std::string> dams_str(n);
  
  // Build ID set and parent map
  for (int i = 0; i < n; i++) {
    std::string id = Rcpp::as<std::string>(ids[i]);
    std::string sire = Rcpp::as<std::string>(sires[i]);
    std::string dam = Rcpp::as<std::string>(dams[i]);
    ids_str[i] = id;
    sires_str[i] = sire;
    dams_str[i] = dam;
    
    id_set.insert(id);
    
    bool has_sire = (sire != "NA" && sire != "0" && sire != "");
    bool has_dam = (dam != "NA" && dam != "0" && dam != "");
    
    parent_map[id] = std::make_pair(
      has_sire ? sire : "",
      has_dam ? dam : ""
    );
  }
  
  // Memoization: cache depth for each ID
  std::unordered_map<std::string, int> depth_cache;
  depth_cache.reserve(n);
  
  // Recursive function to calculate depth with cycle detection
  std::function<int(const std::string&, std::unordered_set<std::string>&)> calc_depth;
  calc_depth = [&](const std::string& id, std::unordered_set<std::string>& visited) -> int {
    if (depth_cache.find(id) != depth_cache.end()) {
      return depth_cache[id];
    }
    
    if (id_set.find(id) == id_set.end()) {
      return 0;
    }
    
    if (visited.find(id) != visited.end()) {
      return 0;
    }
    
    auto it = parent_map.find(id);
    if (it == parent_map.end()) {
      depth_cache[id] = 0;
      return 0;
    }
    
    auto parents = it->second;
    bool has_sire = !parents.first.empty();
    bool has_dam = !parents.second.empty();
    
    if (!has_sire && !has_dam) {
      depth_cache[id] = 0;
      return 0;
    }
    
    visited.insert(id);
    
    int max_parent_depth = 0;
    if (has_sire) {
      int sire_depth = calc_depth(parents.first, visited);
      max_parent_depth = std::max(max_parent_depth, sire_depth);
    }
    if (has_dam) {
      int dam_depth = calc_depth(parents.second, visited);
      max_parent_depth = std::max(max_parent_depth, dam_depth);
    }
    
    visited.erase(id);
    
    int depth = max_parent_depth + 1;
    depth_cache[id] = depth;
    return depth;
  };
  
  IntegerVector depths(n);
  for (int i = 0; i < n; i++) {
    const std::string& id = ids_str[i];
    std::unordered_set<std::string> visited;
    depths[i] = calc_depth(id, visited);
  }
  
  return depths;
}

// Fast descendant summary for parent role (Sire/Dam)
// [[Rcpp::export]]
List fast_descendant_summary(CharacterVector ids,
                             CharacterVector parent_vals,
                             int max_depth = 50) {
  int n = ids.size();
  if (parent_vals.size() != n) {
    Rcpp::stop("Length mismatch: ids and parent_vals must have same length.");
  }
  if (n == 0) {
    return List::create(
      Named("parents") = CharacterVector(),
      Named("totals") = IntegerVector(),
      Named("counts") = IntegerMatrix(0, 0)
    );
  }

  std::unordered_map<std::string, std::vector<int>> parent_children;
  parent_children.reserve(n * 2);
  std::unordered_map<std::string, int> parent_index;
  parent_index.reserve(n);
  std::vector<std::string> parent_ids;
  parent_ids.reserve(n / 2);

  auto is_missing_parent_str = [](const Rcpp::String& s) -> bool {
    if (s == NA_STRING) return true;
    std::string x = std::string(s.get_cstring());
    if (x.empty()) return true;
    if (x == "0") return true;
    if (x == "NA") return true;
    return false;
  };

  for (int i = 0; i < n; ++i) {
    Rcpp::String p = parent_vals[i];
    if (is_missing_parent_str(p)) continue;
    std::string parent_id = std::string(p.get_cstring());
    auto it = parent_index.find(parent_id);
    if (it == parent_index.end()) {
      parent_index[parent_id] = static_cast<int>(parent_ids.size());
      parent_ids.push_back(parent_id);
    }
    parent_children[parent_id].push_back(i);
  }

  int pcount = static_cast<int>(parent_ids.size());
  if (pcount == 0) {
    return List::create(
      Named("parents") = CharacterVector(),
      Named("totals") = IntegerVector(),
      Named("counts") = IntegerMatrix(0, 0)
    );
  }

  IntegerVector totals(pcount);
  IntegerMatrix counts(pcount, max_depth);

  std::vector<int> visit_tag(n, 0);
  int stamp = 1;

  for (int pi = 0; pi < pcount; ++pi) {
    const std::string& root = parent_ids[pi];
    auto it_root = parent_children.find(root);
    if (it_root == parent_children.end() || it_root->second.empty()) {
      totals[pi] = 0;
      continue;
    }

    std::vector<int> current = it_root->second;
    int depth = 1;
    int total = 0;

    while (!current.empty() && depth <= max_depth) {
      std::vector<int> next;
      next.reserve(current.size());
      for (int idx : current) {
        if (visit_tag[idx] == stamp) continue;
        visit_tag[idx] = stamp;
        counts(pi, depth - 1) += 1;
        total += 1;

        const std::string& child_id = Rcpp::as<std::string>(ids[idx]);
        auto it_child = parent_children.find(child_id);
        if (it_child != parent_children.end()) {
          const std::vector<int>& kids = it_child->second;
          next.insert(next.end(), kids.begin(), kids.end());
        }
      }
      current.swap(next);
      depth += 1;
    }

    totals[pi] = total;
    stamp += 1;
    if (stamp == INT_MAX) {
      std::fill(visit_tag.begin(), visit_tag.end(), 0);
      stamp = 1;
    }
  }

  CharacterVector parents(pcount);
  for (int i = 0; i < pcount; ++i) {
    parents[i] = parent_ids[i];
  }

  return List::create(
    Named("parents") = parents,
    Named("totals") = totals,
    Named("counts") = counts
  );
}

static inline std::string trim_copy(const std::string& s) {
  size_t start = 0;
  while (start < s.size() && std::isspace(static_cast<unsigned char>(s[start]))) {
    ++start;
  }
  if (start == s.size()) return "";
  size_t end = s.size() - 1;
  while (end > start && std::isspace(static_cast<unsigned char>(s[end]))) {
    --end;
  }
  return s.substr(start, end - start + 1);
}

static inline bool is_missing_parent(const Rcpp::String& s) {
  if (s == NA_STRING) return true;
  std::string x = trim_copy(std::string(s.get_cstring()));
  if (x.empty()) return true;
  if (x == "0") return true;
  if (x == "NA") return true;
  return false;
}

static inline std::string to_lower_copy(const std::string& s) {
  std::string out = s;
  std::transform(out.begin(), out.end(), out.begin(),
                 [](unsigned char c) { return std::tolower(c); });
  return out;
}

static inline std::string normalize_missing_value(const Rcpp::String& s,
                                                   const std::unordered_set<std::string>& missing_set) {
  if (s == NA_STRING) return "0";
  std::string x = trim_copy(std::string(s.get_cstring()));
  if (x.empty()) return "0";
  std::string lower = to_lower_copy(x);
  if (missing_set.find(lower) != missing_set.end()) return "0";
  return x;
}

// Fast inbreeding coefficients using modified algorithm (C++ implementation)
// [[Rcpp::export]]
NumericVector fast_inbreeding_cpp(CharacterVector ids,
                                  CharacterVector sires,
                                  CharacterVector dams) {
  int n = ids.size();
  if (sires.size() != n || dams.size() != n) {
    Rcpp::stop("Length mismatch: ids, sires, and dams must have same length.");
  }
  if (n == 0) {
    return NumericVector();
  }

  std::unordered_map<std::string, int> id_to_index;
  id_to_index.reserve(n * 2);
  std::vector<std::string> id_vec(n);

  for (int i = 0; i < n; ++i) {
    if (ids[i] == NA_STRING) {
      Rcpp::stop("IDs cannot contain NA values.");
    }
    std::string id = Rcpp::as<std::string>(ids[i]);
    if (id_to_index.find(id) != id_to_index.end()) {
      Rcpp::stop("Duplicate ID found in pedigree: " + id);
    }
    id_to_index[id] = i;
    id_vec[i] = id;
  }

  std::vector<int> sire_idx(n, -1);
  std::vector<int> dam_idx(n, -1);
  std::vector<std::vector<int>> children(n);
  std::vector<int> indegree(n, 0);

  for (int i = 0; i < n; ++i) {
    Rcpp::String s = sires[i];
    Rcpp::String d = dams[i];
    if (!is_missing_parent(s)) {
      std::string sire_id = trim_copy(std::string(s.get_cstring()));
      auto it = id_to_index.find(sire_id);
      if (it != id_to_index.end()) {
        sire_idx[i] = it->second;
        children[it->second].push_back(i);
        indegree[i] += 1;
      }
    }
    if (!is_missing_parent(d)) {
      std::string dam_id = trim_copy(std::string(d.get_cstring()));
      auto it = id_to_index.find(dam_id);
      if (it != id_to_index.end()) {
        dam_idx[i] = it->second;
        children[it->second].push_back(i);
        indegree[i] += 1;
      }
    }
  }

  std::priority_queue<int, std::vector<int>, std::greater<int>> ready;
  for (int i = 0; i < n; ++i) {
    if (indegree[i] == 0) {
      ready.push(i);
    }
  }

  std::vector<int> order;
  order.reserve(n);
  while (!ready.empty()) {
    int node = ready.top();
    ready.pop();
    order.push_back(node);
    for (int child : children[node]) {
      indegree[child] -= 1;
      if (indegree[child] == 0) {
        ready.push(child);
      }
    }
  }

  if ((int)order.size() != n) {
    Rcpp::stop("Cycle detected in pedigree; cannot compute inbreeding coefficients.");
  }

  std::vector<int> new_index(n, 0);
  for (int pos = 0; pos < n; ++pos) {
    new_index[order[pos]] = pos + 1;
  }

  std::vector<int> ped_sire(n + 1, 0);
  std::vector<int> ped_dam(n + 1, 0);
  for (int pos = 1; pos <= n; ++pos) {
    int node = order[pos - 1];
    ped_sire[pos] = (sire_idx[node] >= 0) ? new_index[sire_idx[node]] : 0;
    ped_dam[pos] = (dam_idx[node] >= 0) ? new_index[dam_idx[node]] : 0;
  }

  int m = n;
  std::vector<int> SId(n + 1, 0);
  std::vector<int> Link(n + 1, 0);
  std::vector<int> MaxIdP(n + 1, 0);
  std::vector<double> F(n + 1, 0.0);
  std::vector<double> B(n + 1, 0.0);
  std::vector<double> x(n + 1, 0.0);
  std::vector<int> rPedS(n + 1, 0);
  std::vector<int> rPedD(n + 1, 0);

  F[0] = -1.0;
  x[0] = 0.0;
  Link[0] = 0;
  MaxIdP[0] = 0;

  int rN = 1;
  for (int i = 1; i <= n; ++i) {
    SId[i] = i;
    Link[i] = 0;
    if (i <= m) {
      x[i] = 0.0;
    }
    int S = ped_sire[i];
    int D = ped_dam[i];
    if (S != 0 && Link[S] == 0) {
      MaxIdP[rN] = Link[S] = rN;
      rPedS[rN] = Link[ped_sire[S]];
      rPedD[rN] = Link[ped_dam[S]];
      rN++;
    }
    if (D != 0 && Link[D] == 0) {
      Link[D] = rN;
      rPedS[rN] = Link[ped_sire[D]];
      rPedD[rN] = Link[ped_dam[D]];
      rN++;
    }
    if (MaxIdP[Link[S]] < Link[D]) {
      MaxIdP[Link[S]] = Link[D];
    }
  }

  std::vector<int> sidx;
  sidx.reserve(n);
  for (int i = 1; i <= n; ++i) {
    sidx.push_back(i);
  }
  std::sort(sidx.begin(), sidx.end(), [&](int a, int b) {
    return ped_sire[a] < ped_sire[b];
  });
  for (int i = 1; i <= n; ++i) {
    SId[i] = sidx[i - 1];
  }

  int k = 1;
  int i = 1;
  while (i <= n) {
    if (ped_sire[SId[i]] == 0) {
      F[SId[i]] = 0.0;
      i++;
      continue;
    }

    int S = ped_sire[SId[i]];
    int rS = Link[S];
    if (rS == 0) {
      F[SId[i]] = 0.0;
      i++;
      continue;
    }
    int MIP = MaxIdP[rS];
    x[rS] = 1.0;

    for (; k <= S; ++k) {
      if (Link[k]) {
        B[Link[k]] = 0.5 - 0.25 * (F[ped_sire[k]] + F[ped_dam[k]]);
      }
    }

    for (int j = rS; j >= 1; --j) {
      if (x[j] != 0.0) {
        if (rPedS[j]) x[rPedS[j]] += x[j] * 0.5;
        if (rPedD[j]) x[rPedD[j]] += x[j] * 0.5;
        x[j] *= B[j];
      }
    }

    for (int j = 1; j <= MIP; ++j) {
      x[j] += (x[rPedS[j]] + x[rPedD[j]]) * 0.5;
    }

    for (; i <= n; ++i) {
      if (S != ped_sire[SId[i]]) break;
      int dam_id = ped_dam[SId[i]];
      F[SId[i]] = x[Link[dam_id]] * 0.5;
    }

    for (int j = 1; j <= MIP; ++j) {
      x[j] = 0.0;
    }
  }

  NumericVector result(n);
  for (int idx = 0; idx < n; ++idx) {
    result[idx] = F[new_index[idx]];
  }
  result.attr("names") = ids;
  return result;
}

struct TopAncestorContributionCpp {
  int ancestor_idx;
  double contribution;
  double proportion;
};

static void dfs_paths_cpp(const std::vector<int>& sire_idx,
                          const std::vector<int>& dam_idx,
                          int current_idx,
                          int target_idx,
                          int depth,
                          int max_depth,
                          std::vector<int>& path,
                          std::vector<std::vector<int>>& out) {
  if (depth > max_depth) return;
  if (current_idx == target_idx) {
    out.push_back(path);
    return;
  }
  if (depth == max_depth) return;

  int s = sire_idx[current_idx];
  int d = dam_idx[current_idx];
  if (s >= 0) {
    path.push_back(s);
    dfs_paths_cpp(sire_idx, dam_idx, s, target_idx, depth + 1, max_depth, path, out);
    path.pop_back();
  }
  if (d >= 0) {
    path.push_back(d);
    dfs_paths_cpp(sire_idx, dam_idx, d, target_idx, depth + 1, max_depth, path, out);
    path.pop_back();
  }
}

static std::vector<std::vector<int>> enumerate_paths_cpp(const std::vector<int>& sire_idx,
                                                         const std::vector<int>& dam_idx,
                                                         int start_idx,
                                                         int target_idx,
                                                         int max_depth) {
  std::vector<std::vector<int>> paths;
  std::vector<int> path;
  path.reserve(max_depth + 1);
  path.push_back(start_idx);
  dfs_paths_cpp(sire_idx, dam_idx, start_idx, target_idx, 0, max_depth, path, paths);
  return paths;
}

static bool independent_except_k_cpp(const std::vector<int>& ps,
                                     const std::vector<int>& pd,
                                     int k_idx) {
  std::unordered_set<int> seen;
  for (size_t i = 0; i + 1 < ps.size(); ++i) {
    seen.insert(ps[i]);
  }
  for (size_t j = 0; j + 1 < pd.size(); ++j) {
    int v = pd[j];
    if (v != k_idx && seen.count(v)) return false;
  }
  return true;
}

// Core: compute top-k ancestor contributions for one target (index-based, thread-safe).
static std::vector<TopAncestorContributionCpp> top_contrib_ancestor_core(
    const std::vector<std::string>& id_vec,
    const std::vector<int>& sire_idx,
    const std::vector<int>& dam_idx,
    const std::vector<double>& F_vec,
    int target_idx,
    int max_depth,
    int top_k) {
  int s0 = sire_idx[target_idx];
  int d0 = dam_idx[target_idx];
  if (s0 < 0 || d0 < 0) return std::vector<TopAncestorContributionCpp>();

  std::unordered_set<int> anc_s;
  std::unordered_set<int> anc_d;
  auto collect_all = [&](int start_idx, std::unordered_set<int>& anc) {
    std::vector<int> stack = {start_idx};
    while (!stack.empty()) {
      int cur = stack.back();
      stack.pop_back();
      if (anc.insert(cur).second) {
        int s = sire_idx[cur];
        int d = dam_idx[cur];
        if (s >= 0) stack.push_back(s);
        if (d >= 0) stack.push_back(d);
      }
    }
  };
  collect_all(s0, anc_s);
  collect_all(d0, anc_d);

  struct Tmp { int k_idx; double Ck; };
  std::vector<Tmp> allC;
  allC.reserve(128);

  for (int k_idx : anc_s) {
    if (!anc_d.count(k_idx)) continue;
    auto ps = enumerate_paths_cpp(sire_idx, dam_idx, s0, k_idx, max_depth);
    if (ps.empty()) continue;
    auto pd = enumerate_paths_cpp(sire_idx, dam_idx, d0, k_idx, max_depth);
    if (pd.empty()) continue;
    double Ck = 0.0;
    double factor = 1.0 + F_vec[k_idx];
    for (const auto& p1 : ps) {
      int ns = static_cast<int>(p1.size()) - 1;
      for (const auto& p2 : pd) {
        int nd = static_cast<int>(p2.size()) - 1;
        if (!independent_except_k_cpp(p1, p2, k_idx)) continue;
        int p = ns + nd + 1;
        Ck += std::ldexp(factor, -p);
      }
    }
    if (Ck > 0.0) allC.push_back({k_idx, Ck});
  }

  double F_offspring = 0.0;
  for (const auto& x : allC) F_offspring += x.Ck;
  if (F_offspring <= 0.0) return std::vector<TopAncestorContributionCpp>();

  std::sort(allC.begin(), allC.end(),
            [](const Tmp& a, const Tmp& b) { return a.Ck > b.Ck; });
  int K = std::min(top_k, static_cast<int>(allC.size()));
  std::vector<TopAncestorContributionCpp> out(K);
  for (int i = 0; i < K; ++i) {
    out[i].ancestor_idx = allC[i].k_idx;
    out[i].contribution = allC[i].Ck;
    out[i].proportion = allC[i].Ck / F_offspring;
  }
  return out;
}

// [[Rcpp::export]]
Rcpp::List fast_ancestor_contribution_triplet_cpp(Rcpp::CharacterVector ids,
                                                  Rcpp::CharacterVector sires,
                                                  Rcpp::CharacterVector dams,
                                                  Rcpp::NumericVector F,
                                                  Rcpp::IntegerVector target_indices,
                                                  int top_k = 5,
                                                  int max_depth = 6,
                                                  bool return_ratio = true) {
  int n = ids.size();
  if (sires.size() != n || dams.size() != n || F.size() != n) {
    Rcpp::stop("Length mismatch: ids, sires, dams, and F must have same length.");
  }
  if (n == 0 || target_indices.size() == 0 || top_k <= 0) {
    return Rcpp::List::create(
      Rcpp::Named("i") = Rcpp::IntegerVector(),
      Rcpp::Named("j") = Rcpp::IntegerVector(),
      Rcpp::Named("x") = Rcpp::NumericVector()
    );
  }

  std::unordered_map<std::string, int> id_to_index;
  id_to_index.reserve(n * 2);
  std::vector<std::string> id_vec(n);
  std::vector<int> sire_idx(n, -1);
  std::vector<int> dam_idx(n, -1);
  std::vector<double> F_vec(n);

  for (int i = 0; i < n; ++i) {
    if (ids[i] == NA_STRING) Rcpp::stop("IDs cannot contain NA values.");
    std::string id = Rcpp::as<std::string>(ids[i]);
    if (id_to_index.find(id) != id_to_index.end()) {
      Rcpp::stop("Duplicate ID found in pedigree: " + id);
    }
    id_to_index[id] = i;
    id_vec[i] = id;
    F_vec[i] = static_cast<double>(F[i]);
  }

  for (int i = 0; i < n; ++i) {
    Rcpp::String s = sires[i];
    Rcpp::String d = dams[i];
    if (!is_missing_parent(s)) {
      std::string sire_id = trim_copy(std::string(s.get_cstring()));
      auto it = id_to_index.find(sire_id);
      if (it != id_to_index.end()) sire_idx[i] = it->second;
    }
    if (!is_missing_parent(d)) {
      std::string dam_id = trim_copy(std::string(d.get_cstring()));
      auto it = id_to_index.find(dam_id);
      if (it != id_to_index.end()) dam_idx[i] = it->second;
    }
  }

  std::vector<int> i_idx;
  std::vector<int> j_idx;
  std::vector<double> x_val;
  i_idx.reserve(static_cast<size_t>(target_indices.size()) * static_cast<size_t>(top_k));
  j_idx.reserve(static_cast<size_t>(target_indices.size()) * static_cast<size_t>(top_k));
  x_val.reserve(static_cast<size_t>(target_indices.size()) * static_cast<size_t>(top_k));

  for (int t = 0; t < target_indices.size(); ++t) {
    int idx = target_indices[t] - 1;
    if (idx < 0 || idx >= n) continue;

    if (sire_idx[idx] < 0 || dam_idx[idx] < 0) continue;
    double f_target = F_vec[idx];
    if (!std::isfinite(f_target) || f_target <= 0.0) continue;

    std::vector<TopAncestorContributionCpp> anc = top_contrib_ancestor_core(
      id_vec, sire_idx, dam_idx, F_vec, idx, max_depth, top_k
    );

    for (const auto& a : anc) {
      if (a.ancestor_idx == idx) continue;
      double val = return_ratio ? (a.contribution / f_target) : a.contribution;
      if (!std::isfinite(val) || val == 0.0) continue;
      i_idx.push_back(a.ancestor_idx + 1);
      j_idx.push_back(idx + 1);
      x_val.push_back(val);
    }
  }

  return Rcpp::List::create(
    Rcpp::Named("i") = Rcpp::wrap(i_idx),
    Rcpp::Named("j") = Rcpp::wrap(j_idx),
    Rcpp::Named("x") = Rcpp::wrap(x_val)
  );
}

// [[Rcpp::export]]
Rcpp::DataFrame fast_top_contrib_cpp(Rcpp::CharacterVector ids,
                                     Rcpp::CharacterVector sires,
                                     Rcpp::CharacterVector dams,
                                     Rcpp::NumericVector F,
                                     std::string target_id,
                                     int max_depth = 6,
                                     int top_k = 5) {
  int n = ids.size();
  if (sires.size() != n || dams.size() != n || F.size() != n) {
    Rcpp::stop("Length mismatch: ids, sires, dams, and F must have same length.");
  }
  if (n == 0) {
    return Rcpp::DataFrame::create(
      Rcpp::Named("ancestor_id") = Rcpp::CharacterVector(),
      Rcpp::Named("contribution") = Rcpp::NumericVector(),
      Rcpp::Named("proportion") = Rcpp::NumericVector()
    );
  }

  std::unordered_map<std::string, int> id_to_index;
  id_to_index.reserve(n * 2);
  std::vector<std::string> id_vec(n);

  for (int i = 0; i < n; ++i) {
    if (ids[i] == NA_STRING) {
      Rcpp::stop("IDs cannot contain NA values.");
    }
    std::string id = Rcpp::as<std::string>(ids[i]);
    if (id_to_index.find(id) != id_to_index.end()) {
      Rcpp::stop("Duplicate ID found in pedigree: " + id);
    }
    id_to_index[id] = i;
    id_vec[i] = id;
  }

  auto it_target = id_to_index.find(target_id);
  if (it_target == id_to_index.end()) {
    return Rcpp::DataFrame::create(
      Rcpp::Named("ancestor_id") = Rcpp::CharacterVector(),
      Rcpp::Named("contribution") = Rcpp::NumericVector(),
      Rcpp::Named("proportion") = Rcpp::NumericVector()
    );
  }
  int target_idx = it_target->second;

  std::vector<int> sire_idx(n, -1);
  std::vector<int> dam_idx(n, -1);
  for (int i = 0; i < n; ++i) {
    Rcpp::String s = sires[i];
    Rcpp::String d = dams[i];
    if (!is_missing_parent(s)) {
      std::string sire_id = trim_copy(std::string(s.get_cstring()));
      auto it = id_to_index.find(sire_id);
      if (it != id_to_index.end()) sire_idx[i] = it->second;
    }
    if (!is_missing_parent(d)) {
      std::string dam_id = trim_copy(std::string(d.get_cstring()));
      auto it = id_to_index.find(dam_id);
      if (it != id_to_index.end()) dam_idx[i] = it->second;
    }
  }

  int s0 = sire_idx[target_idx];
  int d0 = dam_idx[target_idx];
  if (s0 < 0 || d0 < 0) {
    return Rcpp::DataFrame::create(
      Rcpp::Named("ancestor_id") = Rcpp::CharacterVector(),
      Rcpp::Named("contribution") = Rcpp::NumericVector(),
      Rcpp::Named("proportion") = Rcpp::NumericVector()
    );
  }

  std::unordered_set<int> anc_s;
  std::unordered_set<int> anc_d;

  auto collect_all = [&](int start_idx, std::unordered_set<int>& anc) {
    std::vector<int> stack = {start_idx};
    while (!stack.empty()) {
      int cur = stack.back();
      stack.pop_back();
      if (anc.insert(cur).second) {
        int s = sire_idx[cur];
        int d = dam_idx[cur];
        if (s >= 0) stack.push_back(s);
        if (d >= 0) stack.push_back(d);
      }
    }
  };

  collect_all(s0, anc_s);
  collect_all(d0, anc_d);

  struct Tmp { int k_idx; double Ck; };
  std::vector<Tmp> allC;
  allC.reserve(128);

  for (int k_idx : anc_s) {
    if (!anc_d.count(k_idx)) continue;

    auto ps = enumerate_paths_cpp(sire_idx, dam_idx, s0, k_idx, max_depth);
    if (ps.empty()) continue;
    auto pd = enumerate_paths_cpp(sire_idx, dam_idx, d0, k_idx, max_depth);
    if (pd.empty()) continue;

    double Ck = 0.0;
    double factor = 1.0 + F[k_idx];

    for (const auto& p1 : ps) {
      int ns = static_cast<int>(p1.size()) - 1;
      for (const auto& p2 : pd) {
        int nd = static_cast<int>(p2.size()) - 1;
        if (!independent_except_k_cpp(p1, p2, k_idx)) continue;
        int p = ns + nd + 1;
        Ck += std::ldexp(factor, -p);
      }
    }

    if (Ck > 0.0) {
      allC.push_back({k_idx, Ck});
    }
  }

  double F_offspring = 0.0;
  for (const auto& x : allC) F_offspring += x.Ck;
  if (F_offspring <= 0.0) {
    return Rcpp::DataFrame::create(
      Rcpp::Named("ancestor_id") = Rcpp::CharacterVector(),
      Rcpp::Named("contribution") = Rcpp::NumericVector(),
      Rcpp::Named("proportion") = Rcpp::NumericVector()
    );
  }

  std::sort(allC.begin(), allC.end(),
            [](const Tmp& a, const Tmp& b) { return a.Ck > b.Ck; });

  int K = std::min(top_k, static_cast<int>(allC.size()));
  Rcpp::CharacterVector ancestor_ids(K);
  Rcpp::NumericVector contributions(K);
  Rcpp::NumericVector proportions(K);

  for (int i = 0; i < K; ++i) {
    ancestor_ids[i] = id_vec[allC[i].k_idx];
    contributions[i] = allC[i].Ck;
    proportions[i] = allC[i].Ck / F_offspring;
  }

  return Rcpp::DataFrame::create(
    Rcpp::Named("ancestor_id") = ancestor_ids,
    Rcpp::Named("contribution") = contributions,
    Rcpp::Named("proportion") = proportions
  );
}

// [[Rcpp::export]]
Rcpp::DataFrame fast_ancestor_contribution_bulk_cpp(Rcpp::CharacterVector ids,
                                                    Rcpp::CharacterVector sires,
                                                    Rcpp::CharacterVector dams,
                                                    Rcpp::NumericVector F,
                                                    int top_k = 5,
                                                    int max_depth = 6,
                                                    bool return_ratio = true) {
  int n = ids.size();
  if (sires.size() != n || dams.size() != n || F.size() != n) {
    Rcpp::stop("Length mismatch: ids, sires, dams, and F must have same length.");
  }
  if (n == 0) {
    Rcpp::CharacterVector id_out(0);
    return Rcpp::DataFrame::create(Rcpp::Named("id") = id_out);
  }

  std::unordered_map<std::string, int> id_to_index;
  id_to_index.reserve(n * 2);
  std::vector<std::string> id_vec(n);
  std::vector<int> sire_idx(n, -1);
  std::vector<int> dam_idx(n, -1);
  std::vector<double> F_vec(n);

  for (int i = 0; i < n; ++i) {
    if (ids[i] == NA_STRING) Rcpp::stop("IDs cannot contain NA values.");
    std::string id = Rcpp::as<std::string>(ids[i]);
    if (id_to_index.find(id) != id_to_index.end()) {
      Rcpp::stop("Duplicate ID found in pedigree: " + id);
    }
    id_to_index[id] = i;
    id_vec[i] = id;
    F_vec[i] = static_cast<double>(F[i]);
  }

  for (int i = 0; i < n; ++i) {
    Rcpp::String s = sires[i];
    Rcpp::String d = dams[i];
    if (!is_missing_parent(s)) {
      std::string sire_id = trim_copy(std::string(s.get_cstring()));
      auto it = id_to_index.find(sire_id);
      if (it != id_to_index.end()) sire_idx[i] = it->second;
    }
    if (!is_missing_parent(d)) {
      std::string dam_id = trim_copy(std::string(d.get_cstring()));
      auto it = id_to_index.find(dam_id);
      if (it != id_to_index.end()) dam_idx[i] = it->second;
    }
  }

  std::vector<int> inbred_indices;
  inbred_indices.reserve(n);
  for (int i = 0; i < n; ++i) {
    if (sire_idx[i] >= 0 && dam_idx[i] >= 0) {
      double fi = F_vec[i];
      if (std::isfinite(fi) && fi > 0.0) inbred_indices.push_back(i);
    }
  }

    std::vector<std::vector<std::string>> result_ids(
      n, std::vector<std::string>(1 + top_k, ""));
    std::vector<std::vector<double>> result_contrib(
      n, std::vector<double>(top_k, NA_REAL));
    for (int i = 0; i < n; ++i) result_ids[i][0] = id_vec[i];

  int ninbred = static_cast<int>(inbred_indices.size());
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic)
#endif
  for (int j = 0; j < ninbred; ++j) {
    int idx = inbred_indices[j];
    std::vector<TopAncestorContributionCpp> anc = top_contrib_ancestor_core(
        id_vec, sire_idx, dam_idx, F_vec, idx, max_depth, top_k);
    double f_target = F_vec[idx];
    for (int a = 0; a < top_k; ++a) {
      if (a < static_cast<int>(anc.size())) {
        result_ids[idx][1 + a] = id_vec[anc[a].ancestor_idx];
        if (return_ratio) {
          if (std::isfinite(f_target) && f_target > 0.0) {
            result_contrib[idx][a] = anc[a].contribution / f_target;
          } else {
            result_contrib[idx][a] = NA_REAL;
          }
        } else {
          result_contrib[idx][a] = anc[a].contribution;
        }
      } else {
        result_ids[idx][1 + a] = "";
        result_contrib[idx][a] = NA_REAL;
      }
    }
  }

  Rcpp::CharacterVector id_out(n);
  std::vector<Rcpp::CharacterVector> anc_cols(top_k);
  std::vector<Rcpp::NumericVector> contrib_cols(top_k);
  for (int k = 0; k < top_k; ++k) anc_cols[k] = Rcpp::CharacterVector(n);
  for (int k = 0; k < top_k; ++k) contrib_cols[k] = Rcpp::NumericVector(n);
  for (int i = 0; i < n; ++i) {
    id_out[i] = result_ids[i][0];
    for (int k = 0; k < top_k; ++k) {
      if (result_ids[i][1 + k].empty())
        anc_cols[k][i] = NA_STRING;
      else
        anc_cols[k][i] = Rcpp::String(result_ids[i][1 + k]);
      contrib_cols[k][i] = result_contrib[i][k];
    }
  }

  Rcpp::List L(1 + 2 * top_k);
  L[0] = id_out;
  for (int k = 0; k < top_k; ++k) {
    L[1 + 2 * k] = anc_cols[k];
    L[1 + 2 * k + 1] = contrib_cols[k];
  }
  Rcpp::CharacterVector nms(1 + 2 * top_k);
  nms[0] = "id";
  for (int k = 0; k < top_k; ++k) {
    nms[1 + 2 * k] = "anc_" + std::to_string(k + 1);
    nms[1 + 2 * k + 1] = "anc_" + std::to_string(k + 1) + "_contribution";
  }
  L.names() = nms;
  return Rcpp::DataFrame(L);
}

// [[Rcpp::export]]
Rcpp::List fast_fix_pedigree_cpp(Rcpp::CharacterVector progeny,
                                 Rcpp::CharacterVector sires,
                                 Rcpp::CharacterVector dams,
                                 Rcpp::Nullable<Rcpp::CharacterVector> sex = R_NilValue,
                                 Rcpp::Nullable<Rcpp::NumericVector> birthdate = R_NilValue,
                                 Rcpp::CharacterVector missing = Rcpp::CharacterVector::create("0", "na", "NA", "", " ")) {
  int n = progeny.size();
  if (sires.size() != n || dams.size() != n) {
    Rcpp::stop("Length mismatch: progeny, sires, and dams must have same length.");
  }

  std::unordered_set<std::string> missing_set;
  missing_set.reserve(missing.size() * 2);
  for (int i = 0; i < missing.size(); ++i) {
    std::string tok = trim_copy(Rcpp::as<std::string>(missing[i]));
    if (!tok.empty()) missing_set.insert(to_lower_copy(tok));
  }

  std::vector<std::string> p(n), s(n), d(n);
  std::vector<std::string> sex_vec;
  std::vector<double> birth_vec;
  if (sex.isNotNull()) {
    Rcpp::CharacterVector sx(sex);
    sex_vec.resize(n);
    for (int i = 0; i < n; ++i) sex_vec[i] = Rcpp::as<std::string>(sx[i]);
  }
  if (birthdate.isNotNull()) {
    Rcpp::NumericVector bd(birthdate);
    birth_vec.resize(n);
    for (int i = 0; i < n; ++i) birth_vec[i] = bd[i];
  }

  for (int i = 0; i < n; ++i) {
    // Progeny/ID: treat user-specified missing tokens (incl. "0") as missing.
    // We represent missing as empty string so it will be dropped below.
    std::string pid = normalize_missing_value(progeny[i], missing_set);
    if (pid == "0") pid.clear();
    p[i] = trim_copy(pid);
    s[i] = normalize_missing_value(sires[i], missing_set);
    d[i] = normalize_missing_value(dams[i], missing_set);
  }

  std::vector<std::string> log_type;
  std::vector<std::string> log_id;
  std::vector<std::string> log_field;
  std::vector<std::string> log_old;
  std::vector<std::string> log_new;

  auto add_log = [&](const std::string& type,
                     const std::string& id,
                     const std::string& field,
                     const std::string& oldv,
                     const std::string& newv) {
    log_type.push_back(type);
    log_id.push_back(id);
    log_field.push_back(field);
    log_old.push_back(oldv);
    log_new.push_back(newv);
  };

  std::vector<int> keep_idx;
  keep_idx.reserve(n);
  for (int i = 0; i < n; ++i) {
    if (p[i].empty()) {
      add_log("missing_progeny", p[i], "row", p[i], "dropped");
      continue;
    }
    keep_idx.push_back(i);
  }

  auto compress = [&](const std::vector<int>& idxs) {
    std::vector<std::string> p2;
    std::vector<std::string> s2;
    std::vector<std::string> d2;
    std::vector<std::string> sex2;
    std::vector<double> birth2;
    p2.reserve(idxs.size());
    s2.reserve(idxs.size());
    d2.reserve(idxs.size());
    if (!sex_vec.empty()) sex2.reserve(idxs.size());
    if (!birth_vec.empty()) birth2.reserve(idxs.size());
    for (int idx : idxs) {
      p2.push_back(p[idx]);
      s2.push_back(s[idx]);
      d2.push_back(d[idx]);
      if (!sex_vec.empty()) sex2.push_back(sex_vec[idx]);
      if (!birth_vec.empty()) birth2.push_back(birth_vec[idx]);
    }
    p.swap(p2);
    s.swap(s2);
    d.swap(d2);
    if (!sex_vec.empty()) sex_vec.swap(sex2);
    if (!birth_vec.empty()) birth_vec.swap(birth2);
  };

  if ((int)keep_idx.size() != n) {
    compress(keep_idx);
  }

  if (p.empty()) {
    Rcpp::DataFrame log_df = Rcpp::DataFrame::create(
      Rcpp::Named("type") = log_type,
      Rcpp::Named("progeny_id") = log_id,
      Rcpp::Named("field") = log_field,
      Rcpp::Named("old") = log_old,
      Rcpp::Named("new") = log_new
    );
    return Rcpp::List::create(
      Rcpp::Named("progeny") = Rcpp::CharacterVector(),
      Rcpp::Named("sire") = Rcpp::CharacterVector(),
      Rcpp::Named("dam") = Rcpp::CharacterVector(),
      Rcpp::Named("sex") = Rcpp::Nullable<Rcpp::CharacterVector>(R_NilValue),
      Rcpp::Named("birthdate") = Rcpp::Nullable<Rcpp::NumericVector>(R_NilValue),
      Rcpp::Named("fix_log") = log_df
    );
  }

  int m = p.size();
  std::vector<int> parent_completeness(m);
  std::vector<int> extra_completeness(m, 0);
  for (int i = 0; i < m; ++i) {
    parent_completeness[i] = (s[i] != "0") + (d[i] != "0");
    if (!sex_vec.empty()) {
      std::string sx = trim_copy(sex_vec[i]);
      if (!sx.empty() && sx != "0" && sx != "NA") extra_completeness[i] += 1;
    }
    if (!birth_vec.empty() && std::isfinite(birth_vec[i]) && birth_vec[i] != 0.0) {
      extra_completeness[i] += 1;
    }
  }

  std::unordered_map<std::string, int> first_idx;
  std::vector<int> keep(m, 0);
  for (int i = 0; i < m; ++i) {
    const std::string& id = p[i];
    auto it = first_idx.find(id);
    if (it == first_idx.end()) {
      first_idx[id] = i;
      keep[i] = 1;
    } else {
      int prev = it->second;
      if (parent_completeness[i] > parent_completeness[prev] ||
          (parent_completeness[i] == parent_completeness[prev] &&
           extra_completeness[i] > extra_completeness[prev])) {
        keep[prev] = 0;
        add_log("duplicate_id", id, "row", "kept_less_complete", "dropped");
        first_idx[id] = i;
        keep[i] = 1;
      } else {
        keep[i] = 0;
        add_log("duplicate_id", id, "row", "duplicate", "dropped");
      }
    }
  }
  if (std::any_of(keep.begin(), keep.end(), [](int v) { return v == 0; })) {
    keep_idx.clear();
    keep_idx.reserve(m);
    for (int i = 0; i < m; ++i) if (keep[i]) keep_idx.push_back(i);
    compress(keep_idx);
  }

  m = p.size();
  for (int i = 0; i < m; ++i) {
    if (s[i] == p[i] && s[i] != "0") {
      add_log("self_parent", p[i], "sire", s[i], "0");
      s[i] = "0";
    }
    if (d[i] == p[i] && d[i] != "0") {
      add_log("self_parent", p[i], "dam", d[i], "0");
      d[i] = "0";
    }
  }

  std::unordered_set<std::string> id_set(p.begin(), p.end());
  std::unordered_set<std::string> add_founders;
  add_founders.reserve(std::max(1, m / 10));
  for (int i = 0; i < m; ++i) {
    if (s[i] != "0" && id_set.find(s[i]) == id_set.end()) {
      add_founders.insert(s[i]);
      add_log("missing_parent_founder", p[i], "sire", s[i], "founder_added");
    }
    if (d[i] != "0" && id_set.find(d[i]) == id_set.end()) {
      add_founders.insert(d[i]);
      add_log("missing_parent_founder", p[i], "dam", d[i], "founder_added");
    }
  }
  if (!add_founders.empty()) {
    size_t add_n = add_founders.size();
    p.reserve(m + add_n);
    s.reserve(m + add_n);
    d.reserve(m + add_n);
    if (!sex_vec.empty()) sex_vec.reserve(m + add_n);
    if (!birth_vec.empty()) birth_vec.reserve(m + add_n);
    for (const auto& pid : add_founders) {
      p.push_back(pid);
      s.push_back("0");
      d.push_back("0");
      id_set.insert(pid);
      if (!sex_vec.empty()) sex_vec.push_back("");
      if (!birth_vec.empty()) birth_vec.push_back(NA_REAL);
    }
    m = static_cast<int>(p.size());
  }

  std::unordered_set<std::string> sire_ids;
  std::unordered_set<std::string> dam_ids;
  for (int i = 0; i < m; ++i) {
    if (s[i] != "0") sire_ids.insert(s[i]);
    if (d[i] != "0") dam_ids.insert(d[i]);
  }
  std::unordered_set<std::string> dual_ids;
  for (const auto& sid : sire_ids) {
    if (dam_ids.find(sid) != dam_ids.end()) dual_ids.insert(sid);
  }
  if (!dual_ids.empty()) {
    for (int i = 0; i < m; ++i) {
      if (dual_ids.find(s[i]) != dual_ids.end() && s[i] != "0") {
        add_log("dual_role_parent", p[i], "sire", s[i], "0");
        s[i] = "0";
      }
      if (dual_ids.find(d[i]) != dual_ids.end() && d[i] != "0") {
        add_log("dual_role_parent", p[i], "dam", d[i], "0");
        d[i] = "0";
      }
    }
  }

  if (!sex_vec.empty()) {
    Rcpp::List qc_sex = fast_pedigree_qc_sex(
      Rcpp::wrap(p), Rcpp::wrap(s), Rcpp::wrap(d), Rcpp::wrap(sex_vec)
    );
    Rcpp::CharacterVector bad_sires = qc_sex["sex_mismatch_sire_ids"];
    Rcpp::CharacterVector bad_dams = qc_sex["sex_mismatch_dam_ids"];
    std::unordered_set<std::string> bad_sire_set;
    std::unordered_set<std::string> bad_dam_set;
    bad_sire_set.reserve(bad_sires.size() * 2);
    bad_dam_set.reserve(bad_dams.size() * 2);
    for (int i = 0; i < bad_sires.size(); ++i) {
      if (bad_sires[i] != NA_STRING) {
        bad_sire_set.insert(Rcpp::as<std::string>(bad_sires[i]));
      }
    }
    for (int i = 0; i < bad_dams.size(); ++i) {
      if (bad_dams[i] != NA_STRING) {
        bad_dam_set.insert(Rcpp::as<std::string>(bad_dams[i]));
      }
    }
    if (!bad_sire_set.empty() || !bad_dam_set.empty()) {
      for (int i = 0; i < m; ++i) {
        if (s[i] != "0" && bad_sire_set.find(s[i]) != bad_sire_set.end()) {
          add_log("sex_mismatch", p[i], "sire", s[i], "0");
          s[i] = "0";
        }
        if (d[i] != "0" && bad_dam_set.find(d[i]) != bad_dam_set.end()) {
          add_log("sex_mismatch", p[i], "dam", d[i], "0");
          d[i] = "0";
        }
      }
    }
  }

  if (!birth_vec.empty()) {
    Rcpp::List birth_res = check_birth_date_order(
      Rcpp::wrap(p), Rcpp::wrap(s), Rcpp::wrap(d), Rcpp::wrap(birth_vec)
    );
    Rcpp::CharacterVector bad_children = birth_res["invalid_offspring_ids"];
    std::unordered_map<std::string, int> idx_map;
    idx_map.reserve(m * 2);
    for (int i = 0; i < m; ++i) idx_map[p[i]] = i;

    int n_bad = bad_children.size();
    for (int i = 0; i < n_bad; ++i) {
      if (bad_children[i] == NA_STRING) continue;
      std::string child_id = Rcpp::as<std::string>(bad_children[i]);
      auto it = idx_map.find(child_id);
      if (it == idx_map.end()) continue;
      int child_idx = it->second;
      double old_bd = birth_vec[child_idx];
      if (std::isfinite(old_bd) && old_bd != 0.0) {
        add_log("birthdate_invalid", child_id, "birthdate", std::to_string(old_bd), "0");
      }
      birth_vec[child_idx] = 0.0;
    }
  }

  Rcpp::List loops = fast_detect_loops(Rcpp::wrap(p), Rcpp::wrap(s), Rcpp::wrap(d));
  int loop_count = loops["count"];
  if (loop_count > 0) {
    Rcpp::List cycles = loops["cycles"];
    std::unordered_map<std::string, int> idx_map;
    idx_map.reserve(m * 2);
    for (int i = 0; i < m; ++i) idx_map[p[i]] = i;
    for (int ci = 0; ci < cycles.size(); ++ci) {
      Rcpp::CharacterVector cyc = cycles[ci];
      std::unordered_set<std::string> nodes;
      for (int j = 0; j < cyc.size(); ++j) {
        nodes.insert(Rcpp::as<std::string>(cyc[j]));
      }
      int child_idx = -1;
      for (const auto& node : nodes) {
        auto it = idx_map.find(node);
        if (it != idx_map.end()) {
          if (child_idx < 0 || it->second > child_idx) child_idx = it->second;
        }
      }
      if (child_idx < 0) continue;
      std::string child_id = p[child_idx];
      if (nodes.find(s[child_idx]) != nodes.end() && s[child_idx] != "0") {
        add_log("loop_break", child_id, "sire", s[child_idx], "0");
        s[child_idx] = "0";
      } else if (nodes.find(d[child_idx]) != nodes.end() && d[child_idx] != "0") {
        add_log("loop_break", child_id, "dam", d[child_idx], "0");
        d[child_idx] = "0";
      }
    }
  }

  Rcpp::DataFrame log_df = Rcpp::DataFrame::create(
    Rcpp::Named("type") = log_type,
    Rcpp::Named("progeny_id") = log_id,
    Rcpp::Named("field") = log_field,
    Rcpp::Named("old") = log_old,
    Rcpp::Named("new") = log_new
  );

  Rcpp::CharacterVector out_p = Rcpp::wrap(p);
  Rcpp::CharacterVector out_s = Rcpp::wrap(s);
  Rcpp::CharacterVector out_d = Rcpp::wrap(d);
  Rcpp::RObject out_sex = R_NilValue;
  Rcpp::RObject out_birth = R_NilValue;
  if (!sex_vec.empty()) {
    Rcpp::CharacterVector sx_out(sex_vec.size());
    for (size_t i = 0; i < sex_vec.size(); ++i) {
      if (sex_vec[i].empty()) {
        sx_out[i] = NA_STRING;
      } else {
        sx_out[i] = sex_vec[i];
      }
    }
    out_sex = sx_out;
  }
  if (!birth_vec.empty()) out_birth = Rcpp::wrap(birth_vec);

  return Rcpp::List::create(
    Rcpp::Named("progeny") = out_p,
    Rcpp::Named("sire") = out_s,
    Rcpp::Named("dam") = out_d,
    Rcpp::Named("sex") = out_sex,
    Rcpp::Named("birthdate") = out_birth,
    Rcpp::Named("fix_log") = log_df
  );
}
