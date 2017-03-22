package readers;

import java.util.List;

import model.Player;
import model.Thing;
import model.criteria.Criteria;

public interface CriteriaReader {

	public Criteria readCriteria(List<Thing> things, List<Player> players, String criteriaData);
	public List<Criteria> readCriteriaList(List<Thing> things, List<Player> players, String gameData);
}
