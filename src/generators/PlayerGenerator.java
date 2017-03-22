package generators;

import java.util.List;

import model.Player;
import model.tree.Tree;

public interface PlayerGenerator {

	public Player generatePlayer(List<Tree> trees);

	public Player generatePlayer(String name, int agentHealth, int agentSpeed, int agentPower, List<Tree> trees);

	public Player generatePlayer(String name, List<Tree> trees);
}
