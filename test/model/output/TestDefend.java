package model.output;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import org.junit.After;
import org.junit.Test;

import junit.framework.TestCase;
import main.Game;
import model.Agent;
import model.Map;
import model.output.Action.Activity;
import readers.ActionReaderImpl;
import readers.CriteriaReaderImpl;
import readers.GameReader;
import readers.GameReaderImpl;
import readers.InputReaderImpl;
import readers.MapReaderImpl;
import readers.ModeReaderImpl;
import readers.PlantReaderImpl;
import readers.PlayerReaderImpl;
import readers.PositionReaderImpl;
import readers.TreeReaderImpl;

public class TestDefend extends TestCase {

	private GameReader gameReader;
	private final ByteArrayOutputStream outContent = new ByteArrayOutputStream();

	@Override
	protected void setUp() {
		gameReader = new GameReaderImpl(new MapReaderImpl(new PlantReaderImpl(),
				new PlayerReaderImpl(new TreeReaderImpl(new ActionReaderImpl(new PositionReaderImpl()), new InputReaderImpl(new PositionReaderImpl()))),
				new CriteriaReaderImpl(new ActionReaderImpl(new PositionReaderImpl())), new ModeReaderImpl()));
		System.setOut(new PrintStream(outContent));
	}
	
	@After
	public void cleanUpStreams() {
	    System.setOut(null);
	}

	/**
	 * http://stackoverflow.com/questions/1119385/junit-test-for-system-out-println
	 */
	@Test
	public void testDefend_Success_NoAttack() {
		String file = "resources\\test\\outputMaps\\test_defend_success_noattack.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.DEFEND);
		assertTrue(map.getAllAgents().size() == 1);
	}
	
	@Test
	public void testDefend_Success_Attack() {
		String file = "resources\\test\\outputMaps\\test_defend_success_attack.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		Agent attacker = map.getAllAgents().get(1);
		
		assertTrue(agent.update(map));
		assertTrue(attacker.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.DEFEND);
		assertTrue(agent.getHealth() == 5);
		assertTrue(map.getAllAgents().size() == 2);
	}	
}
